using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Buffers.Binary;
using Newtonsoft.Json;
using TS3AudioBot;
using TS3AudioBot.Plugins;
using TS3AudioBot.CommandSystem;
using TSLib;
using TSLib.Audio;
using TSLib.Full;

namespace TS3AudioBot.Plugins
{
    public class SpeechRecorderPlugin : IBotPlugin
    {
        private static readonly NLog.Logger Log = NLog.LogManager.GetCurrentClassLogger();

        public Bot Bot { get; set; }
        public TsFullClient TsFullClient { get; set; }
        public Ts3Client Ts3Client { get; set; }

        // ==========================================
        // 【配置区】 你可以在这里随时修改录音参数
        // ==========================================
        
        // true = WAV格式 (自带文件头，双击可播), false = PCM纯数据流
        private const bool EXPORT_AS_WAV = true;
        
        // 说话断句的静音等待时间 (毫秒)。1000 = 停顿1秒钟即封包切割
        private const int SILENCE_SPLIT_MS = 1000;
        
        // 频道内无任何语音活动的自动停止时间 (毫秒)。600000 = 10分钟
        private const int AUTO_STOP_TIMEOUT_MS = 600000;

        // ==========================================

        private class UserRecordState
        {
            public FileStream AudioStream { get; set; }
            public DateTime StartTime { get; set; }
            public DateTime LastSpeakTime { get; set; }
            public string FileName { get; set; }
            public string ClientName { get; set; }
            public bool IsClosed { get; set; }
        }

        public class JsonRecordEntry
        {
            public ushort ClientId { get; set; }
            public string ClientName { get; set; }
            public string StartTime { get; set; }
            public string EndTime { get; set; }
            public double DurationMs { get; set; }
            public double StartOffsetMs { get; set; }
            public string AudioFile { get; set; }
        }

        private ConcurrentDictionary<ushort, UserRecordState> _activeRecords;
        private List<JsonRecordEntry> _sessionRecords;
        
        private bool _isPluginRunning;
        private bool _isRecordingEnabled;
        private string _currentSessionFolder;
        private MyVoiceReceiver _voiceReceiver;
        private DateTime _lastGlobalVoiceTime;
        private DateTime _sessionStartTime;
        private readonly object _jsonLock = new object();

        public void Initialize()
        {
            _activeRecords = new ConcurrentDictionary<ushort, UserRecordState>();
            _sessionRecords = new List<JsonRecordEntry>();
            _isPluginRunning = true;
            _isRecordingEnabled = false;

            Task.Run(() => SilenceDetectorLoop());
            string formatInfo = EXPORT_AS_WAV ? "WAV (48kHz 16-bit Stereo 双声道)" : "PCM";
            Log.Info($"[STT录音插件] 加载成功！导出格式: {formatInfo}");
        }

        [Command("stt")]
        public string CommandStt(string action)
        {
            if (action.ToLower() == "start")
            {
                if (_isRecordingEnabled) return "录音已经在进行中了！";

                if (TsFullClient != null)
                {
                    if (_voiceReceiver == null)
                    {
                        _voiceReceiver = new MyVoiceReceiver();
                        TsFullClient.OutStream = _voiceReceiver;
                        Log.Info("[STT录音插件] 已成功装载 Opus 解码管道！");
                    }

                    _voiceReceiver.OnVoiceData -= HandleUserVoiceData;
                    _voiceReceiver.OnVoiceData += HandleUserVoiceData;
                }
                else
                {
                    return "🔴 启动失败：无法获取底层客户端。";
                }

                string timeStr = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                _currentSessionFolder = Path.Combine("Recordings", $"Session_{timeStr}");
                Directory.CreateDirectory(_currentSessionFolder);

                _sessionRecords.Clear();
                _isRecordingEnabled = true;
                _sessionStartTime = DateTime.Now;
                _lastGlobalVoiceTime = _sessionStartTime;

                string fmt = EXPORT_AS_WAV ? "WAV" : "PCM";
                return $"🔴 已开始多角色语音录制！({fmt} 双声道模式)\n保存路径: {_currentSessionFolder}\n⚠️ 若超过 10 分钟无人说话将自动停止。";
            }
            else if (action.ToLower() == "stop")
            {
                if (!_isRecordingEnabled) return "当前没有在录音。";

                _isRecordingEnabled = false;

                foreach (var kvp in _activeRecords)
                {
                    CloseAndSaveRecord(kvp.Key, kvp.Value);
                }
                _activeRecords.Clear();

                return $"⏹ 已停止录音！\n所有文件及 index.json 已保存至: {_currentSessionFolder}";
            }
            else
            {
                return "⚠️ 未知指令。请使用 !stt start 或 !stt stop";
            }
        }

        private string GetClientName(ushort clientId)
        {
            try
            {
                if (TsFullClient != null)
                {
                    var book = TsFullClient.GetType().GetProperty("Book")?.GetValue(TsFullClient);
                    if (book != null)
                    {
                        var clientsObj = book.GetType().GetProperty("Clients")?.GetValue(book);
                        if (clientsObj is IDictionary dict)
                        {
                            foreach (DictionaryEntry entry in dict)
                            {
                                var clientObj = entry.Value;
                                var idObj = clientObj.GetType().GetProperty("Id")?.GetValue(clientObj);
                                if (idObj != null)
                                {
                                    var valObj = idObj.GetType().GetProperty("Value")?.GetValue(idObj);
                                    if (valObj is ushort val && val == clientId)
                                    {
                                        var name = clientObj.GetType().GetProperty("Name")?.GetValue(clientObj) as string 
                                                ?? clientObj.GetType().GetProperty("Nickname")?.GetValue(clientObj) as string;
                                        if (!string.IsNullOrWhiteSpace(name)) return name;
                                    }
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception ex) { Log.Debug(ex, "[STT] 通过 Book 查询客户端 {0} 昵称失败", clientId); }

            try
            {
                if (Ts3Client != null)
                {
                    var field = Ts3Client.GetType().GetField("clientbuffer", BindingFlags.NonPublic | BindingFlags.Instance);
                    if (field != null && field.GetValue(Ts3Client) is IEnumerable buffer)
                    {
                        foreach (var clientObj in buffer)
                        {
                            var idObj = clientObj.GetType().GetProperty("ClientId")?.GetValue(clientObj);
                            if (idObj != null)
                            {
                                var valObj = idObj.GetType().GetProperty("Value")?.GetValue(idObj);
                                if (valObj is ushort val && val == clientId)
                                {
                                    var name = clientObj.GetType().GetProperty("Name")?.GetValue(clientObj) as string 
                                            ?? clientObj.GetType().GetProperty("Nickname")?.GetValue(clientObj) as string;
                                    if (!string.IsNullOrWhiteSpace(name)) return name;
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception ex) { Log.Debug(ex, "[STT] 通过 clientbuffer 查询客户端 {0} 昵称失败", clientId); }

            return $"UnknownUser_{clientId}";
        }

        private void HandleUserVoiceData(ushort clientId, byte[] audioData)
        {
            if (!_isRecordingEnabled) return;

            var now = DateTime.Now;
            _lastGlobalVoiceTime = now; 

            var userState = _activeRecords.GetOrAdd(clientId, id =>
            {
                string clientName = GetClientName(id);
                long startOffsetMs = (long)(now - _sessionStartTime).TotalMilliseconds;
                string safeClientName = string.Concat(clientName.Split(Path.GetInvalidFileNameChars()));
                string extension = EXPORT_AS_WAV ? ".wav" : ".pcm";
                string fileName = $"{startOffsetMs:D8}ms_{safeClientName}{extension}";
                string filePath = Path.Combine(_currentSessionFolder, fileName);

                var stream = new FileStream(filePath, FileMode.Create, FileAccess.Write, FileShare.Read);
                
                if (EXPORT_AS_WAV)
                {
                    stream.Write(new byte[44], 0, 44);
                }

                return new UserRecordState
                {
                    AudioStream = stream,
                    StartTime = now,
                    LastSpeakTime = now,
                    FileName = fileName,
                    ClientName = clientName
                };
            });

            lock (userState.AudioStream)
            {
                if (userState.IsClosed) return;
                userState.AudioStream.Write(audioData, 0, audioData.Length);
                userState.LastSpeakTime = now;
            }
        }

        private void WriteWavHeader(FileStream stream, int dataLength)
        {
            stream.Seek(0, SeekOrigin.Begin);
            using (var writer = new BinaryWriter(stream, Encoding.ASCII, true))
            {
                writer.Write(Encoding.ASCII.GetBytes("RIFF"));
                writer.Write(36 + dataLength);
                writer.Write(Encoding.ASCII.GetBytes("WAVE"));
                writer.Write(Encoding.ASCII.GetBytes("fmt "));
                writer.Write(16);
                writer.Write((short)1);
                writer.Write((short)2);
                writer.Write(48000);
                writer.Write(48000 * 2 * 2);
                writer.Write((short)4);
                writer.Write((short)16);
                writer.Write(Encoding.ASCII.GetBytes("data"));
                writer.Write(dataLength);
            }
        }

        private void CloseAndSaveRecord(ushort clientId, UserRecordState state)
        {
            lock (state.AudioStream)
            {
                if (state.IsClosed) return;
                state.IsClosed = true;

                if (EXPORT_AS_WAV)
                {
                    int dataLength = (int)state.AudioStream.Length - 44;
                    WriteWavHeader(state.AudioStream, dataLength);
                }

                state.AudioStream.Flush();
                state.AudioStream.Close();
                state.AudioStream.Dispose();
            }

            double startOffsetMs = (state.StartTime - _sessionStartTime).TotalMilliseconds;

            var entry = new JsonRecordEntry
            {
                ClientId = clientId,
                ClientName = state.ClientName,
                StartTime = state.StartTime.ToString("yyyy-MM-dd HH:mm:ss.fff"),
                EndTime = state.LastSpeakTime.ToString("yyyy-MM-dd HH:mm:ss.fff"),
                DurationMs = Math.Round((state.LastSpeakTime - state.StartTime).TotalMilliseconds, 2),
                StartOffsetMs = Math.Round(startOffsetMs, 2),
                AudioFile = state.FileName
            };

            lock (_jsonLock)
            {
                _sessionRecords.Add(entry);
                SaveJsonIndex();
            }
        }

        private void SaveJsonIndex()
        {
            if (string.IsNullOrEmpty(_currentSessionFolder)) return;

            string jsonPath = Path.Combine(_currentSessionFolder, "index.json");
            string jsonString = JsonConvert.SerializeObject(_sessionRecords, Formatting.Indented);
            File.WriteAllText(jsonPath, jsonString);
        }

        private async Task SilenceDetectorLoop()
        {
            while (_isPluginRunning)
            {
                if (_isRecordingEnabled)
                {
                    var now = DateTime.Now;

                    if ((now - _lastGlobalVoiceTime).TotalMilliseconds > AUTO_STOP_TIMEOUT_MS)
                    {
                        Log.Info("[STT录音插件] 超过规定时间无语音活动，触发自动停止录制。");
                        
                        try 
                        {
                            if (Ts3Client != null) 
                            {
                                _ = Ts3Client.SendChannelMessage($"⏹ 超过 {AUTO_STOP_TIMEOUT_MS / 60000} 分钟无语音活动，已自动停止录音并封包。");
                            }
                        } 
                        catch (Exception ex) { Log.Warn(ex, "[STT] 发送自动停止频道通知消息失败"); }

                        CommandStt("stop");
                        continue; 
                    }
                    
                    var stoppedUsers = _activeRecords
                        .Where(kvp => (now - kvp.Value.LastSpeakTime).TotalMilliseconds > SILENCE_SPLIT_MS)
                        .ToList();

                    foreach (var kvp in stoppedUsers)
                    {
                        if (_activeRecords.TryRemove(kvp.Key, out var state))
                        {
                            CloseAndSaveRecord(kvp.Key, state);
                        }
                    }
                }
                await Task.Delay(200);
            }
        }

        public void Dispose()
        {
            _isPluginRunning = false;
            
            if (_voiceReceiver != null)
            {
                _voiceReceiver.OnVoiceData -= HandleUserVoiceData;
                _voiceReceiver.Dispose();
                
                if (TsFullClient != null && TsFullClient.OutStream == _voiceReceiver)
                {
                    TsFullClient.OutStream = null;
                }
            }

            if (_isRecordingEnabled)
                CommandStt("stop");
        }

        public class MyVoiceReceiver : IAudioPassiveConsumer, IDisposable
        {
            public bool Active => true;
            public event Action<ushort, byte[]> OnVoiceData;

            private DecoderPipe _decoderPipe;
            private MyDecoderConsumer _consumer;

            public MyVoiceReceiver()
            {
                _decoderPipe = new DecoderPipe();
                _consumer = new MyDecoderConsumer(this);
                _decoderPipe.OutStream = _consumer;
            }

            public void Write(Span<byte> data, Meta meta)
            {
                // 【修复点1】: 拦截并丢弃过短的信号包（防止数组越界和 Opus 报错）
                if (data.Length <= 5) return;

                ushort clientId = BinaryPrimitives.ReadUInt16BigEndian(data.Slice(2, 2));
                byte codecByte = data[4];

                meta ??= new Meta();
                
                meta.In = new MetaIn { Sender = (TSLib.ClientId)clientId, Whisper = meta.In.Whisper };

                if (codecByte == 4) meta.Codec = TSLib.Codec.OpusVoice;
                else if (codecByte == 5) meta.Codec = TSLib.Codec.OpusMusic;
                else return; 

                // 【修复点2】: 增加异常捕捉层。
                // 这样即使收到加密错误、丢包或异常的控制网络包，插件只会安静地丢弃它，绝不让程序崩溃！
                try
                {
                    _decoderPipe.Write(data.Slice(5), meta);
                }
                catch (Exception ex)
                {
                    Log.Debug(ex, "[STT] 已丢弃来自客户端 {0} 的异常音频包", clientId);
                }
            }

            public void Dispose()
            {
                _decoderPipe?.Dispose();
            }

            private class MyDecoderConsumer : IAudioPassiveConsumer
            {
                public bool Active => true;
                private MyVoiceReceiver _parent;

                public MyDecoderConsumer(MyVoiceReceiver parent)
                {
                    _parent = parent;
                }

                public void Write(Span<byte> data, Meta meta)
                {
                    if (meta != null && meta.In.Sender.Value != 0)
                    {
                        _parent.OnVoiceData?.Invoke(meta.In.Sender.Value, data.ToArray());
                    }
                }
            }
        }
    }
}
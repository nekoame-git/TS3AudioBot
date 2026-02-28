using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using TS3AudioBot;
using TS3AudioBot.Plugins;
using TS3AudioBot.CommandSystem;
using TSLib.Audio;
using TSLib.Full;
using Newtonsoft.Json;

namespace TS3AudioBot.Plugins
{
    public class SpeechRecorderPlugin : IBotPlugin
    {
        private static readonly NLog.Logger Log = NLog.LogManager.GetCurrentClassLogger();

        public Bot Bot { get; set; }
        public TsFullClient TsFullClient { get; set; }
        public Ts3Client Ts3Client { get; set; }

        private class UserRecordState
        {
            public FileStream AudioStream { get; set; }
            public DateTime StartTime { get; set; }
            public DateTime LastSpeakTime { get; set; }
            public string FileName { get; set; }
            public string ClientName { get; set; }
        }

        public class JsonRecordEntry
        {
            public ushort ClientId { get; set; }
            public string ClientName { get; set; }
            public string StartTime { get; set; }
            public string EndTime { get; set; }
            public double DurationMs { get; set; }
            public string AudioFile { get; set; }
        }

        private ConcurrentDictionary<ushort, UserRecordState> _activeRecords;
        private List<JsonRecordEntry> _sessionRecords;
        
        private bool _isPluginRunning;
        private bool _isRecordingEnabled;
        private string _currentSessionFolder;
        private ClientMixdown _mixdownInstance;
        private readonly object _jsonLock = new object();

        public void Initialize()
        {
            _activeRecords = new ConcurrentDictionary<ushort, UserRecordState>();
            _sessionRecords = new List<JsonRecordEntry>();
            _isPluginRunning = true;
            _isRecordingEnabled = false;

            Task.Run(() => SilenceDetectorLoop());
            Log.Info("[STT录音插件] 加载成功！");
        }

        private ClientMixdown FindMixdown(object obj, int depth = 0)
        {
            if (obj == null || depth > 10) return null;
            if (obj is ClientMixdown mix) return mix;

            var outStreamProp = obj.GetType().GetProperty("OutStream", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (outStreamProp != null)
            {
                var next = outStreamProp.GetValue(obj);
                var res = FindMixdown(next, depth + 1);
                if (res != null) return res;
            }

            if (obj is IEnumerable enumerable)
            {
                foreach (var item in enumerable)
                {
                    var res = FindMixdown(item, depth + 1);
                    if (res != null) return res;
                }
            }
            return null;
        }

        [Command("stt start")]
        public string CommandStartRecording()
        {
            if (_isRecordingEnabled) return "录音已经在进行中了！";

            if (TsFullClient != null)
            {
                // 1. 尝试寻找现有的音频管道
                _mixdownInstance = FindMixdown(TsFullClient.OutStream);
                
                // 2. 核心修复：如果没找到（因为 TS3AudioBot 默认不处理接收语音）
                // 我们自己创建一个混音器，并强行插进 TsFullClient 的 OutStream 接收口！
                if (_mixdownInstance == null)
                {
                    _mixdownInstance = new ClientMixdown();
                    
                    if (TsFullClient.OutStream == null)
                    {
                        TsFullClient.OutStream = _mixdownInstance;
                        Log.Info("[STT录音插件] 原生音频管道为空，已成功装载全新的 ClientMixdown！");
                    }
                    else
                    {
                        // 万一有别的不知道什么管道占着，我们强行覆盖接管
                        TsFullClient.OutStream = _mixdownInstance;
                        Log.Info("[STT录音插件] 已覆盖现有音频管道并装载 ClientMixdown！");
                    }
                }

                // 3. 挂载我们在 TSLib 里加的后门事件
                _mixdownInstance.OnUserVoiceDataReceived -= HandleUserVoiceData;
                _mixdownInstance.OnUserVoiceDataReceived += HandleUserVoiceData;
            }
            else
            {
                return "🔴 启动失败：无法获取底层客户端，请确认机器人已连接服务器。";
            }

            string timeStr = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            _currentSessionFolder = Path.Combine("Recordings", $"Session_{timeStr}");
            Directory.CreateDirectory(_currentSessionFolder);

            _sessionRecords.Clear();
            _isRecordingEnabled = true;

            return $"🔴 已开始多角色语音录制！\n保存路径: {_currentSessionFolder}";
        }

        [Command("stt stop")]
        public string CommandStopRecording()
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

        private string GetClientName(ushort clientId)
        {
            try
            {
                if (Ts3Client != null)
                {
                    var method = Ts3Client.GetType().GetMethod("GetCachedClientById") 
                              ?? Ts3Client.GetType().GetMethod("GetClientById")
                              ?? Ts3Client.GetType().GetMethod("GetClientInfoById");
                              
                    if (method != null)
                    {
                        var info = method.Invoke(Ts3Client, new object[] { clientId });
                        if (info != null)
                        {
                            var nickProp = info.GetType().GetProperty("Nickname") ?? info.GetType().GetProperty("Name");
                            if (nickProp != null)
                            {
                                string nickname = nickProp.GetValue(info) as string;
                                if (!string.IsNullOrWhiteSpace(nickname)) return nickname;
                            }
                        }
                    }
                }
            }
            catch { }
            return $"UnknownUser_{clientId}";
        }

        private void HandleUserVoiceData(ushort clientId, byte[] audioData)
        {
            if (!_isRecordingEnabled) return;

            var now = DateTime.Now;

            var userState = _activeRecords.GetOrAdd(clientId, id =>
            {
                string startTimeStr = now.ToString("yyyy-MM-dd_HH-mm-ss.fff");
                string clientName = GetClientName(id);
                string fileName = $"{startTimeStr}_{id}.pcm";
                string filePath = Path.Combine(_currentSessionFolder, fileName);

                return new UserRecordState
                {
                    AudioStream = new FileStream(filePath, FileMode.Create, FileAccess.Write, FileShare.Read),
                    StartTime = now,
                    LastSpeakTime = now,
                    FileName = fileName,
                    ClientName = clientName
                };
            });

            lock (userState.AudioStream)
            {
                userState.AudioStream.Write(audioData, 0, audioData.Length);
                userState.LastSpeakTime = now;
            }
        }

        private void CloseAndSaveRecord(ushort clientId, UserRecordState state)
        {
            lock (state.AudioStream)
            {
                state.AudioStream.Flush();
                state.AudioStream.Close();
                state.AudioStream.Dispose();
            }

            var entry = new JsonRecordEntry
            {
                ClientId = clientId,
                ClientName = state.ClientName,
                StartTime = state.StartTime.ToString("yyyy-MM-dd HH:mm:ss.fff"),
                EndTime = state.LastSpeakTime.ToString("yyyy-MM-dd HH:mm:ss.fff"),
                DurationMs = Math.Round((state.LastSpeakTime - state.StartTime).TotalMilliseconds, 2),
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
                    var stoppedUsers = _activeRecords
                        .Where(kvp => (now - kvp.Value.LastSpeakTime).TotalMilliseconds > 1000)
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
            if (_mixdownInstance != null)
                _mixdownInstance.OnUserVoiceDataReceived -= HandleUserVoiceData;

            if (_isRecordingEnabled)
                CommandStopRecording();
        }
    }
}
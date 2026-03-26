# More logs
When diagnosing a problem a detailed log can be often helpful to pinpoint the exact cause.
To get the full output navigate to the `NLog.config` file which is located in the same folder as the `TS3AudioBot.exe` you use to run the bot.
Then overwrite content with the following template:
```xml
<?xml version="1.0" encoding="utf-8" ?>
<nlog xmlns="http://www.nlog-project.org/schemas/NLog.xsd"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      throwConfigExceptions="true">

	<targets>
		<!-- Config log to file -->
		<target xsi:type="File"
		        name="logfile"
		        encoding="utf-8"
		        fileName="${currentdir}/logs/ts3audiobot_${cached:${date:format=yyyy-MM-dd_HH_mm_ss}}.log"
		        layout="${longdate}|${pad:padding=5:inner=${level:uppercase=true}}|${mdlc:item=BotId}|${callsite:includeNamespace=false} ${message}${onexception:${newline}${exception:format=tostring}}" />
		<!-- Config log to console -->
		<target xsi:type="ColoredConsole"
		        name="console"
		        encoding="utf-8"
		        layout="${time}|${pad:padding=5:inner=${level:uppercase=true}}|${mdlc:item=BotId}| ${message}">
			<highlight-row condition="level == LogLevel.Info" foregroundColor="Cyan"/>
			<highlight-row condition="level == LogLevel.Warn" foregroundColor="Yellow"/>
			<highlight-row condition="level == LogLevel.Error" foregroundColor="Red"/>
			<highlight-row condition="level == LogLevel.Fatal" foregroundColor="Magenta"/>
		</target>
	</targets>

	<rules>
		<!-- TS3AudioBot related logs -->
		<logger name="TS3AudioBot.*" minlevel="Debug" writeTo="logfile" />
		<logger name="TS3AudioBot.*" minlevel="Debug" writeTo="console" />
		<!-- TS3Client related logs -->
		<logger name="TSLib.*" minlevel="Debug" writeTo="logfile" />
		<logger name="TSLib.*" minlevel="Debug" writeTo="console" />
	</rules>
</nlog>
```

You can also set the `minlevel` to `Trace` for both when the case requires it.
This is usually not necessary and will bloat the output a lot.
Use it only when asked by a project member for an issue or when you really need the most detailed output. 
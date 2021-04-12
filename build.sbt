libraryDependencies += "com.bot4s" %% "telegram-core" % "4.4.0-RC2"
libraryDependencies += "io.spray" %%  "spray-json" % "1.3.6"
libraryDependencies ++= Seq(
    "net.debasishg" %% "redisclient" % "3.30"
)
enablePlugins(JavaAppPackaging)
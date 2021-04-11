import scala.concurrent.Await
import scala.concurrent.duration.Duration
import slogging.{LogLevel, LoggerConfig, PrintLogger, PrintLoggerFactory}
object Main {
  def main(args: Array[String]): Unit = {
    LoggerConfig.factory = PrintLoggerFactory()
    LoggerConfig.level = LogLevel.INFO

    val madriletaBot = new MadriletaBot()
    val eol = madriletaBot.run()
    println("Press [ENTER] to shutdown the bot, it may take a few seconds...")
    scala.io.StdIn.readLine()
    madriletaBot.shutdown() // initiate shutdown
    // Wait for the bot end-of-life
    Await.result(eol, Duration.Inf)
  }
}

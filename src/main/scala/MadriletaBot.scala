import com.bot4s.telegram.future.{Polling, TelegramBot}
import scalaj.http._
import com.bot4s.telegram.api.RequestHandler
import com.bot4s.telegram.api.declarative.Commands
import com.bot4s.telegram.clients.ScalajHttpClient
import com.bot4s.telegram.methods.SendMessage

import com.redis._

import scala.concurrent.Future
import scala.util.{Success, Failure}
import java.util.concurrent.ScheduledThreadPoolExecutor
import java.util.concurrent.TimeUnit
import com.bot4s.telegram.methods.SendMessage
import com.bot4s.telegram.models.ChatType
import scala.concurrent.duration.Duration
import scala.concurrent.Await

class MadriletaBot extends TelegramBot with Polling with Commands[Future] {

  logger.info("Initializing MadriletaBot...")

  private val externalData = new ExternalDataReader()

  // Set Telegram connection
  override val client: RequestHandler[Future] = new ScalajHttpClient(
    externalData.token
  )

  val openWeatherMapApiUrl =
    s"https://api.openweathermap.org/data/2.5/weather"

  def getWeatherInfo(): Future[HttpResponse[String]] = {
    logger.debug("Querying OpenWeatherMap")
    return Future {
      Http(openWeatherMapApiUrl)
        .param("q", "Madrid")
        .param("appid", externalData.mapApiKey)
        .param("lang", "es")
        .asString
    }
  }

  // Check if there is a connection to OMW, if not throw exception
  getWeatherInfo() onComplete {
    case Success(response) =>
      logger.debug("Successful connection to OpenWeatherMap")
    case Failure(t) =>
      throw new RuntimeException(
        "Couldn't connect to OpenWeatherMap: " + t.getMessage
      )
  }

  // Redis connection for saving subscriptions
  val redis =
    new RedisClient(externalData.redisURL, externalData.redisPort)
  def subscribe(chatId: Long) = Future {
    redis.set(chatId, 1)
  }
  def unsubscribe(chatId: Long) = Future {
    redis.del(chatId)
  }

  // Set commands

  onCommand("tiempo") { implicit msg =>
    for {
      r <- getWeatherInfo()
      if r.isSuccess
    } yield reply(OWMPatternMatcher.matchWeather(r.body))
  }

  onCommand("subscribirse") { implicit msg =>
    for {
      r <- subscribe(msg.source)
    } yield { reply("Te has subscrito correctamente") }
  }

  onCommand("desubscribirse") { implicit msg =>
    for {
      r <- unsubscribe(msg.source)
    } yield { reply("Te has desubscrito correctamente") }
  }

  onCommand("notificar") { implicit msg =>
    if (
      msg.chat.`type`
        .equals(ChatType.Private) && msg.from.get.id.equals(externalData.creator)
    ) {
      for {
        r <- getWeatherInfo()
      } yield broadcaster.sendMessage(OWMPatternMatcher.matchWeather(r.body))
    } else {
      Future {
        reply("No eres el creador del bot")
      }
    }
  }

  private var broadcaster: MessageBroadcaster =
    new MessageBroadcaster(redis, request)

  private var lastMessage: String = ""

  // Listens to the weather API and sends a message when the weather isn't clear or cloudy
  // 1 query/6 s ~= 10 queries/min ~= 500000 queries/month, half of the allowed free tier

  val messageRunnerExecutor = new ScheduledThreadPoolExecutor(1)
  val runner = messageRunnerExecutor.scheduleAtFixedRate(
    () => {
      val getWeather = for {
        r <- getWeatherInfo()
        if r.isSuccess
      } yield OWMPatternMatcher.matchWeather(r.body)

      getWeather foreach { msg =>
        // If the last message that has already been sent is equal to the last received message, don't send it (avoid spam)
        if (!lastMessage.equals(msg)) {
          lastMessage = msg
          if (
            !lastMessage.equals(SpanishPhrasesEnum.cieloClaro) && !lastMessage
              .equals(SpanishPhrasesEnum.nublado)
          ) {
            broadcaster.sendMessage(lastMessage)
          }
        }
      }
    },
    0,
    6,
    TimeUnit.SECONDS
  )
  // TODO: Añadir por qué

  override def shutdown() {
    messageRunnerExecutor.shutdown()
    if (broadcaster != null) {
      broadcaster.shutdown()
    }
    return super.shutdown()
  }

  logger.info("MadriletaBot initialized")

}

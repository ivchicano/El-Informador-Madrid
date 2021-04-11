import java.util.concurrent.ScheduledThreadPoolExecutor
import java.util.concurrent.TimeUnit
import com.bot4s.telegram.methods.SendMessage
import com.redis.RedisClient
import slogging.StrictLogging
import com.bot4s.telegram.api.RequestHandler
import scala.concurrent.Future
import java.util.concurrent.ScheduledFuture

class MessageBroadcaster(redis: RedisClient, request: RequestHandler[Future])
    extends StrictLogging {
  private var i: Int = 0
  private var chatIds: List[Option[String]] = null
  private var message: String = null

  private val messageSenderExecutor = new ScheduledThreadPoolExecutor(1)
  private val runnable = new Runnable {
    def run() {
      if (message != null) {
        logger.debug("Iteration " + i)
        logger.debug("chatIds size " + chatIds.size)
        if (i <= chatIds.size - 1) {
          try {
            logger.debug("Sending message to: " + chatIds(i))
            request(SendMessage(chatIds(i).get, message))
          } catch {
            case e: Exception =>
              logger.error(
                "Error while broadcasting messages: " + e.printStackTrace()
              )
          }
          i += 1
        } else {
          logger.debug("All messages sent")
          message = null
        }
      }
    }
  }
  private val runner: ScheduledFuture[_] =
    messageSenderExecutor.scheduleAtFixedRate(
      runnable,
      0,
      100,
      TimeUnit.MILLISECONDS
    )

  def sendMessage(message: String) {
    i = 0
    chatIds = redis.keys("*").get
    this.message = message
  }

  def shutdown() {
    if (!messageSenderExecutor.isShutdown()) {
      messageSenderExecutor.shutdown()
    }
  }
}

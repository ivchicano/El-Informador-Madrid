import scala.io.Source
import java.io.FileNotFoundException
import slogging.StrictLogging

class ExternalDataReader extends StrictLogging {

  private def getFromEnvVars(key: String) = {
    scala.util.Properties
      .envOrNone(key)
      .getOrElse(
        throw new RuntimeException(
          s"Environment variable ${key} needs to be set"
        )
      )
  }

  var token: String = null
  var mapApiKey: String = null
  var redisURL: String = null
  var redisPort: Int = -1
  var creator: Int = -1

  try {
    def envFromFile: Map[String, String] =
      Source
        .fromFile(".env")
        .getLines()
        .map(x => x.split("=")(0) -> x.split("=")(1))
        .toMap
    token = envFromFile.get("BOT_TOKEN").getOrElse(getFromEnvVars("BOT_TOKEN"))
    logger.debug("BOT_TOKEN: " + token)
    mapApiKey = envFromFile.get("MAP_KEY").getOrElse(getFromEnvVars("MAP_KEY"))
    logger.debug("MAP_KEY: " + mapApiKey)
    redisURL =
      envFromFile.get("REDIS_URL").getOrElse(getFromEnvVars("REDIS_URL"))
    logger.debug("REDIS_URL: " + redisURL)
    redisPort = envFromFile
      .get("REDIS_PORT")
      .getOrElse(getFromEnvVars("REDIS_PORT"))
      .toInt
    logger.debug("REDIS_PORT: " + redisPort)
    creator = envFromFile
      .get("CREATOR")
      .getOrElse(getFromEnvVars("CREATOR"))
      .toInt
    logger.debug("CREATOR: " + creator)

  } catch {
    case e: Exception => {
      logger.debug("Couldn't get data from file: " + e.getMessage())
      token = getFromEnvVars("BOT_TOKEN")
      logger.debug("BOT_TOKEN: " + token)
      mapApiKey = getFromEnvVars("MAP_KEY")
      logger.debug("MAP_KEY: " + mapApiKey)
      redisURL = getFromEnvVars("REDIS_URL")
      logger.debug("REDIS_URL: " + redisURL)
      redisPort = getFromEnvVars("REDIS_PORT").toInt
      logger.debug("REDIS_PORT: " + redisPort)
      creator = getFromEnvVars("CREATOR").toInt
      logger.debug("CREATOR: " + creator)
    }
  }
}

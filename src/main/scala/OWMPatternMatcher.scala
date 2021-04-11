import spray.json._
import DefaultJsonProtocol._

object OWMPatternMatcher {
  def matchWeather(body: String): String =
    body.parseJson.asJsObject
      .fields("weather")
      .asInstanceOf[JsArray]
      .elements(0)
      .asJsObject
      .fields("main")
      .convertTo[String] match {
      case "Thunderstorm" => SpanishPhrasesEnum.tormenta
      case "Drizzle"      => SpanishPhrasesEnum.lloviendo
      case "Rain"         => SpanishPhrasesEnum.lloviendo
      case "Snow"         => SpanishPhrasesEnum.nevando
      case "Clouds"       => SpanishPhrasesEnum.nublado
      case "Clear"        => SpanishPhrasesEnum.cieloClaro
      case _ =>
        body.parseJson.asJsObject
          .fields("weather")
          .asInstanceOf[JsArray]
          .elements(0)
          .asJsObject
          .fields("description") + " en Madrid"
    }
}

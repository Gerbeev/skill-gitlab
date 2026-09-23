package bank.risk

object RiskWriter {
  def writeExposure(amount: Double): Unit = {
    val query = "INSERT INTO risk.daily_exposure VALUES (1)"
    println(query)
  }
}

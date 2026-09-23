CREATE OR REPLACE PROCEDURE reporting.generate_report AS
BEGIN
  SELECT exposure INTO current_exposure FROM risk.daily_exposure;
  INSERT INTO reporting.daily_report VALUES (current_exposure);
END;

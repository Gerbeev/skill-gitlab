CREATE OR REPLACE PACKAGE BODY payment_pkg AS
  PROCEDURE run IS
  BEGIN
    ledger_pkg.post_entry;
    CALL audit_pkg.log_run('payment');
    EXECUTE payment_staging.flush;
  END run;
END payment_pkg;
/

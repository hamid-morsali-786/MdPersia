<dev dir="rtl">

<div dir="rtl">

# طرح قدم به قدم پیاده‌سازی برای پروسیجر `DMSP_GLUPDATE_CORE` و کل فرایند EOD

</div>

<div dir="rtl">

> هدف اولیه: **کاهش زمان رفع خطا (MTTR) از ۲–۸ ساعت به ۱۰–۳۰ دقیقه** برای ۹۰٪ خطاهای رایج.

</div>

<div dir="rtl">

طرح در ۴ فاز و ۱۲ مرحله سازمان‌دهی شده. هر مرحله شامل:
- **چه می‌کنیم**
- **چرا** (دلیل تجاری/فنی)
- **چطور** (نمونهٔ SQL/PL/SQL)
- **زمان تخمینی**
- **معیار پذیرش (Definition of Done)**

</div>

---

<div dir="rtl">

## فاز ۰ — Quick-Wins (۳ تا ۵ روز کاری)

</div>

<div dir="rtl">

این فاز **بدون هیچ تغییری در منطق پروسیجر**، صرفاً با اضافه کردن لایهٔ Logging و Instrumentation، **بیش از ۶۰٪ از کاهش MTTR را به‌دست می‌دهد**. اگر فقط یک فاز را اجرا کنید، این فاز را اجرا کنید.

</div>

---

<div dir="rtl">

### مرحلهٔ ۱ — تکمیل ساختار جدول‌های لاگ

</div>

<div dir="rtl">

**چه می‌کنیم:**  
ستون‌های ضروری زیر را به جداول لاگ موجود اضافه می‌کنیم. این تغییر **non-breaking** است (همه ستون‌های جدید Nullable).

</div>

```sql
-- ستون‌های جدید برای DAYEND_PROCLOG_TABLE
ALTER TABLE DATAMATE.DAYEND_PROCLOG_TABLE ADD (
    BANK              VARCHAR2(4 CHAR),
    EOD_DATE          DATE,
    STEP_NAME         VARCHAR2(100 CHAR),
    SQLCODE_VAL       NUMBER,
    BACKTRACE         CLOB,
    CALL_STACK        CLOB,
    BIND_VARS         VARCHAR2(4000 CHAR),
    ROWS_PROCESSED    NUMBER,
    DB_SID            NUMBER,
    DB_SERIAL         NUMBER,
    OS_USER           VARCHAR2(60 CHAR),
    HOST_NAME         VARCHAR2(60 CHAR),
    SEVERITY          VARCHAR2(10 CHAR)   -- INFO / WARN / ERROR / FATAL
);

-- ستون‌های جدید برای DAYENDEXEC (نگه‌داری Context حتی پس از خطا)
ALTER TABLE DATAMATE.DAYENDEXEC ADD (
    EOD_STATUS        VARCHAR2(20 CHAR) DEFAULT 'RUNNING',
    LAST_PROC         VARCHAR2(60 CHAR),
    LAST_STEP         VARCHAR2(100 CHAR),
    UPDATED_AT        TIMESTAMP DEFAULT SYSTIMESTAMP,
    STARTED_AT        TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- ستون‌های جدید برای DAYENDLOG
ALTER TABLE DATAMATE.DAYENDLOG ADD (
    SQLCODE_VAL       NUMBER,
    BACKTRACE         CLOB,
    DURATION_SEC      NUMBER
);

-- جدول جدید برای Step-Level Logging
CREATE TABLE DATAMATE.DAYEND_STEPLOG (
    STEP_ID           NUMBER GENERATED ALWAYS AS IDENTITY,
    BANK              VARCHAR2(4 CHAR),
    EOD_DATE          DATE,
    PROC_NAME         VARCHAR2(60 CHAR),
    STEP_NAME         VARCHAR2(100 CHAR),
    STEP_STATUS       VARCHAR2(20 CHAR),  -- STARTED / COMPLETED / FAILED / SKIPPED
    STARTED_AT        TIMESTAMP,
    ENDED_AT          TIMESTAMP,
    DURATION_SEC      NUMBER GENERATED ALWAYS AS (
        EXTRACT(SECOND FROM (ENDED_AT - STARTED_AT)) +
        EXTRACT(MINUTE FROM (ENDED_AT - STARTED_AT)) * 60 +
        EXTRACT(HOUR   FROM (ENDED_AT - STARTED_AT)) * 3600
    ) VIRTUAL,
    ROWS_PROCESSED    NUMBER,
    BIND_VARS         VARCHAR2(4000 CHAR),
    SQLCODE_VAL       NUMBER,
    SQLERRM_VAL       VARCHAR2(4000 CHAR),
    BACKTRACE         CLOB,
    CALL_STACK        CLOB,
    DB_SID            NUMBER,
    DB_SERIAL         NUMBER,
    PAYLOAD_JSON      CLOB,                -- وضعیت میانی (JSON)
    CONSTRAINT PK_DAYEND_STEPLOG PRIMARY KEY (STEP_ID)
)
TABLESPACE DATAMATE_TBS;

CREATE INDEX IDX_STEPLOG_LOOKUP   ON DATAMATE.DAYEND_STEPLOG (BANK, EOD_DATE, PROC_NAME, STEP_NAME);
CREATE INDEX IDX_STEPLOG_STATUS   ON DATAMATE.DAYEND_STEPLOG (STEP_STATUS, STARTED_AT);

-- جدول Checkpoint برای Restartability
CREATE TABLE DATAMATE.DAYEND_CHECKPOINT (
    BANK              VARCHAR2(4 CHAR),
    EOD_DATE          DATE,
    PROC_NAME         VARCHAR2(60 CHAR),
    STEP_NAME         VARCHAR2(100 CHAR),
    STEP_STATUS       VARCHAR2(20 CHAR),
    COMPLETED_AT      TIMESTAMP,
    ROWS_PROCESSED    NUMBER,
    PAYLOAD_JSON      CLOB,
    CONSTRAINT PK_DAYEND_CHECKPOINT PRIMARY KEY (BANK, EOD_DATE, PROC_NAME, STEP_NAME)
)
TABLESPACE DATAMATE_TBS;
```

<div dir="rtl">

**چرا:**  
- بدون این ستون‌ها، نمی‌دانید "خطا برای کدام بانک، کدام تاریخ، کدام Step، با چه Bind Vars رخ داد".
- BACKTRACE تنها راه فهمیدن **خط دقیق** خطاست.
- Step-level logging به شما اجازه می‌دهد در هر زمان ببینید الان دقیقاً کجای ۳۵۹۱ خط در حال اجراست.

</div>

<div dir="rtl">

**زمان:** ۴ ساعت  
**معیار پذیرش:** همهٔ DDLها روی محیط Test اجرا شده‌اند، Index ها ساخته شده‌اند، هیچ‌چیز از منطق فعلی نشکسته است.

</div>

---

<div dir="rtl">

### مرحلهٔ ۲ — ساخت Package سراسری `DMSP_LOG_PKG`

</div>

<div dir="rtl">

**چه می‌کنیم:**  
یک Package می‌سازیم که همهٔ پروسیجرها از آن برای Logging استفاده می‌کنند. این Package از `PRAGMA AUTONOMOUS_TRANSACTION` استفاده می‌کند تا حتی پس از Rollback پروسیجر اصلی، Logها حفظ شوند.

</div>

```sql
CREATE OR REPLACE PACKAGE DATAMATE.DMSP_LOG_PKG AS

    -- Severity levels
    G_INFO  CONSTANT VARCHAR2(10) := 'INFO';
    G_WARN  CONSTANT VARCHAR2(10) := 'WARN';
    G_ERROR CONSTANT VARCHAR2(10) := 'ERROR';
    G_FATAL CONSTANT VARCHAR2(10) := 'FATAL';

    -- شروع یک Step
    PROCEDURE log_step_start(
        p_bank      IN VARCHAR2,
        p_eod_date  IN DATE,
        p_proc_name IN VARCHAR2,
        p_step_name IN VARCHAR2,
        p_bind_vars IN VARCHAR2 DEFAULT NULL
    );

    -- پایان موفق یک Step
    PROCEDURE log_step_end(
        p_bank          IN VARCHAR2,
        p_eod_date      IN DATE,
        p_proc_name     IN VARCHAR2,
        p_step_name     IN VARCHAR2,
        p_rows_processed IN NUMBER DEFAULT NULL,
        p_payload_json  IN CLOB    DEFAULT NULL
    );

    -- ثبت خطا (با Backtrace کامل)
    PROCEDURE log_error(
        p_bank      IN VARCHAR2,
        p_eod_date  IN DATE,
        p_proc_name IN VARCHAR2,
        p_step_name IN VARCHAR2,
        p_bind_vars IN VARCHAR2 DEFAULT NULL,
        p_severity  IN VARCHAR2 DEFAULT G_ERROR
    );

    -- ثبت یک پیام عمومی (INFO/WARN)
    PROCEDURE log_message(
        p_bank      IN VARCHAR2,
        p_eod_date  IN DATE,
        p_proc_name IN VARCHAR2,
        p_step_name IN VARCHAR2,
        p_message   IN VARCHAR2,
        p_severity  IN VARCHAR2 DEFAULT G_INFO
    );

    -- بررسی Checkpoint (آیا قبلاً موفق اجرا شده؟)
    FUNCTION is_step_completed(
        p_bank      IN VARCHAR2,
        p_eod_date  IN DATE,
        p_proc_name IN VARCHAR2,
        p_step_name IN VARCHAR2
    ) RETURN BOOLEAN;

    -- ثبت Checkpoint موفق
    PROCEDURE save_checkpoint(
        p_bank          IN VARCHAR2,
        p_eod_date      IN DATE,
        p_proc_name     IN VARCHAR2,
        p_step_name     IN VARCHAR2,
        p_rows_processed IN NUMBER DEFAULT NULL,
        p_payload_json  IN CLOB    DEFAULT NULL
    );

END DMSP_LOG_PKG;
/
```

<div dir="rtl">

پیاده‌سازی Body در فایل `03_refactored_procedure_template.md` آمده.

</div>

<div dir="rtl">

**چرا:**  
- **یک نقطهٔ مرکزی** برای Logging؛ تغییر فرمت یا destination در یک جا انجام می‌شود.
- **Autonomous Transaction** تضمین می‌کند Logها حفظ می‌شوند حتی هنگام Rollback.
- **Standardization**: همهٔ ۵۴ پروسیجر از یک API یکسان استفاده می‌کنند.

</div>

<div dir="rtl">

**زمان:** ۸ ساعت  
**معیار پذیرش:** تست واحد Package روی محیط Test، عملکرد در صورت Rollback پروسیجر اصلی.

</div>

---

<div dir="rtl">

### مرحلهٔ ۳ — افزودن `EXCEPTION WHEN OTHERS` سراسری به `DMSP_GLUPDATE_CORE`

</div>

<div dir="rtl">

**چه می‌کنیم:**  
بلاک سراسری `EXCEPTION WHEN OTHERS` به انتهای `BEGIN ... END;` اصلی پروسیجر اضافه می‌شود تا هر خطای Unhandled به‌صورت ساختاری Log شود.

</div>

```sql
-- در حال حاضر پایان پروسیجر در خط ۳۵۸۹ بدون EXCEPTION:
END;
/

-- تغییر به:
EXCEPTION
    WHEN OTHERS THEN
        DMSP_LOG_PKG.log_error(
            p_bank      => inpbank,
            p_eod_date  => inpcurrentday,
            p_proc_name => 'DMSP_GLUPDATE_CORE',
            p_step_name => NVL(SYS_CONTEXT('USERENV','ACTION'), 'TOP-LEVEL'),
            p_bind_vars => 'inpbank='||inpbank||',inpcurrentday='||TO_CHAR(inpcurrentday,'YYYY-MM-DD'),
            p_severity  => DMSP_LOG_PKG.G_FATAL
        );
        outresult  := -1;
        outmessage := 'GLUPDATE_CORE failed: '||SUBSTR(SQLERRM, 1, 200);
END;
/
```

<div dir="rtl">

**چرا:**  
الان اگر در خط ۲۹۰۰ یک `ORA-01403: no data found` رخ دهد، خطا به Caller پرتاب می‌شود ولی **هیچ Backtrace ذخیره نمی‌شود**. با این بلاک، حتی اگر Caller هم خطا را Log کند، شما **نقطهٔ دقیق** را در `DAYEND_STEPLOG` خواهید داشت.

</div>

<div dir="rtl">

**زمان:** ۱ ساعت  
**معیار پذیرش:** یک خطای ساختگی در Test ایجاد کنید، رکورد ERROR در `DAYEND_STEPLOG` با BACKTRACE درست ثبت شود.

</div>

---

<div dir="rtl">

### مرحلهٔ ۴ — اصلاح Trigger `TR_DAYENDLOG`

</div>

<div dir="rtl">

**چه می‌کنیم:**  
به‌جای حذف رکورد از `DAYENDEXEC` هنگام شکست، وضعیت آن را به‌روزرسانی می‌کنیم.

</div>

```sql
CREATE OR REPLACE TRIGGER DATAMATE.TR_DAYENDLOG
   AFTER UPDATE OF EXECUTIONFAILED
   ON DATAMATE.DAYENDLOG
   FOR EACH ROW
BEGIN
   IF :NEW.EXECUTIONFAILED = 'Y' THEN
      -- قبلاً: DELETE FROM DAYENDEXEC;
      -- جدید: نگه‌داریم Context را برای Forensics
      UPDATE DAYENDEXEC SET
         EOD_STATUS = 'FAILED',
         LAST_PROC  = :NEW.PROCNAME,
         UPDATED_AT = SYSTIMESTAMP;
   END IF;
END;
/
```

<div dir="rtl">

**چرا:**  
رفتار فعلی Trigger شما (`DELETE FROM DAYENDEXEC`) باعث می‌شود **Context عملیاتی پاک شود**. این یعنی هنگام Forensics باید با حدس و گمان از روی DAYENDLOG بانک و تاریخ EOD را بازسازی کنید. با این تغییر، رکورد می‌ماند ولی `EOD_STATUS = 'FAILED'` می‌شود.

</div>

<div dir="rtl">

> توجه: اگر منطق فعلی شما به این `DELETE` متکی است (مثلاً کد Caller پس از مشاهدهٔ خالی بودن `DAYENDEXEC` می‌فهمد EOD متوقف شده)، باید آن کد را به بررسی `EOD_STATUS = 'FAILED'` تغییر دهید.

</div>

<div dir="rtl">

**زمان:** ۱ ساعت + ۲ ساعت تست رگرسیون  
**معیار پذیرش:** پس از شکست EOD، رکورد `DAYENDEXEC` با `EOD_STATUS='FAILED'` می‌ماند.

</div>

---

<div dir="rtl">

### مرحلهٔ ۵ — ساخت View داشبورد

</div>

<div dir="rtl">

**چه می‌کنیم:**  
یک View برای دیدن وضعیت Real-Time در یک نگاه.

</div>

```sql
CREATE OR REPLACE VIEW V_DAYEND_DASHBOARD AS
SELECT 
    de.BANK,
    de.DAYENDDATE                                   AS EOD_DATE,
    de.EOD_STATUS,
    de.STARTED_AT,
    ROUND((SYSTIMESTAMP - de.STARTED_AT) * 24*60, 1)  AS RUNNING_MINUTES,
    de.LAST_PROC,
    de.LAST_STEP,
    (SELECT COUNT(*) FROM DAYENDLOG d WHERE d.EXECUTIONDATE = de.DAYENDDATE)                       AS TOTAL_PROCS,
    (SELECT COUNT(*) FROM DAYENDLOG d WHERE d.EXECUTIONDATE = de.DAYENDDATE AND d.EXECUTIONFLAG='Y') AS DONE_PROCS,
    (SELECT COUNT(*) FROM DAYENDLOG d WHERE d.EXECUTIONDATE = de.DAYENDDATE AND d.EXECUTIONFAILED='Y') AS FAILED_PROCS,
    (SELECT MAX(p.SQLERRM_VAL) FROM DAYEND_STEPLOG p
      WHERE p.BANK = de.BANK AND p.EOD_DATE = de.DAYENDDATE AND p.STEP_STATUS = 'FAILED')           AS LAST_ERROR
FROM DAYENDEXEC de;
```

<div dir="rtl">

و یک View برای Step هایی که در حال اجرا هستند:

</div>

```sql
CREATE OR REPLACE VIEW V_DAYEND_RUNNING_STEPS AS
SELECT 
    s.BANK,
    s.EOD_DATE,
    s.PROC_NAME,
    s.STEP_NAME,
    s.STARTED_AT,
    ROUND((SYSTIMESTAMP - s.STARTED_AT) * 24*60, 1) AS RUNNING_MINUTES,
    s.DB_SID,
    s.DB_SERIAL,
    v.STATUS                                         AS DB_SESSION_STATUS,
    v.BLOCKING_SESSION,
    v.EVENT,
    v.SQL_ID
FROM DAYEND_STEPLOG s
LEFT JOIN V$SESSION v ON v.SID = s.DB_SID AND v.SERIAL# = s.DB_SERIAL
WHERE s.STEP_STATUS = 'STARTED'
  AND s.STARTED_AT > SYSTIMESTAMP - INTERVAL '1' DAY;
```

<div dir="rtl">

**چرا:**  
این دو View به Operations اجازه می‌دهند با **یک Query** ببینند:
- EOD کجاست؟ موفق/شکست/در حال اجرا؟
- چند پروسیجر مانده؟
- چه قدر طول کشیده؟
- آیا Session ها Block هستند؟

</div>

<div dir="rtl">

**زمان:** ۲ ساعت  
**معیار پذیرش:** اجرای `SELECT * FROM V_DAYEND_DASHBOARD` در حین EOD وضعیت Real-Time را نشان دهد.

</div>

---

<div dir="rtl">

## فاز ۱ — Instrumentation کامل (۱ تا ۲ هفته)

</div>

<div dir="rtl">

### مرحلهٔ ۶ — افزودن `DBMS_APPLICATION_INFO` به همهٔ پروسیجرها

</div>

<div dir="rtl">

**چه می‌کنیم:**  
در ابتدای هر پروسیجر، Module تنظیم شود؛ در ابتدای هر بلاک منطقی، Action تنظیم شود.

</div>

```sql
-- در ابتدای پروسیجر
DBMS_APPLICATION_INFO.SET_MODULE(
    module_name => 'DMSP_GLUPDATE_CORE',
    action_name => 'INIT'
);
DBMS_APPLICATION_INFO.SET_CLIENT_INFO('Bank='||inpbank||',Date='||TO_CHAR(inpcurrentday,'YYYY-MM-DD'));

-- در ابتدای هر بلاک منطقی
DBMS_APPLICATION_INFO.SET_ACTION('YEAREND-INSERT-GLBALANCE');
-- ... DML ...
DBMS_APPLICATION_INFO.SET_ACTION('CASH-GL-UPDATE');
-- ... DML ...
```

<div dir="rtl">

**چرا:**  
بدون این، Operations هنگام مشاهدهٔ Session در `V$SESSION` فقط می‌بیند `MODULE = NULL`. با این تغییر، یک Query ساده روی `V$SESSION` می‌گوید الان دقیقاً کجای کار هستیم.

</div>

<div dir="rtl">

**زمان:** ۲ روز کاری برای کل ۵۴ پروسیجر  
**معیار پذیرش:** در حین EOD، `SELECT module, action, client_info FROM V$SESSION WHERE module LIKE 'DMSP_%'` خروجی غنی بدهد.

</div>

---

<div dir="rtl">

### مرحلهٔ ۷ — تقسیم `DMSP_GLUPDATE_CORE` به بلاک‌های منطقی Step-Logged

</div>

<div dir="rtl">

**چه می‌کنیم:**  
پروسیجر را به ۱۲ Step منطقی تقسیم می‌کنیم. هر Step `log_step_start`/`log_step_end`/`log_error` را صدا می‌زند.

</div>

<div dir="rtl">

پیشنهاد تقسیم پروسیجر فعلی:

</div>

<div dir="rtl">

| # | Step Name | محدودهٔ خط | شرح |
|---|-----------|------------|------|
| 1 | `INIT-LOAD-PARAMS` | ۳۰۲–۳۴۷ | بارگذاری holiday/specialstatus/yearend |
| 2 | `YEAREND-BULK-INSERT-GLBAL` | ۳۶۰–۸۹۳ | INSERT حجیم در Year-End |
| 3 | `INSERT-GLACCOUNTBAL-NONYEAREND` | ۹۸۵–۱۲۵۴ | INSERT برای روزهای عادی |
| 4 | `UPDATE-OPENINGBAL-FROM-PREV` | ۱۲۵۶–۱۵۳۴ | Update Opening Balance |
| 5 | `UPDATE-GENERALLEDGER-OPENING` | ۱۵۸۰–۱۵۹۶ | Update GL Opening |
| 6 | `RECON-GL-UPDATE` | ۱۵۹۹–۱۶۲۱ | Reconciliation GL |
| 7 | `TEMPGL-DIFFERENCE-FIRST` | ۱۶۲۴–۱۷۲۸ | TempGL Pass 1 |
| 8 | `TEMPGL-DIFFERENCE-SECOND` | ۱۷۳۱–۱۸۸۲ | TempGL Pass 2 |
| 9 | `INTEREST-ACCRUAL-SHIFT` | ۱۸۸۶–۱۸۹۸ | فراخوانی پروسیجرهای SBYREND/TDYREND |
| 10 | `BULK-CURRENCY-FALLBACK` | ۲۶۲۴–۲۶۴۰ | FORALL با SAVE EXCEPTIONS |
| 11 | `TEMPGL-FINAL-RECONCILE` | ۳۳۰۵–۳۵۲۸ | پاس نهایی TempGL |
| 12 | `CASH-RETENTION-LOG-YEARBEGIN` | ۳۵۳۰–۳۵۸۸ | لاگ سقف نقد + اصلاح Year Begin |

</div>

<div dir="rtl">

برای هر Step، الگو:

</div>

```sql
-- شروع Step
DBMS_APPLICATION_INFO.SET_ACTION('STEP-7-TEMPGL-DIFF-FIRST');
DMSP_LOG_PKG.log_step_start(inpbank, inpcurrentday, 'DMSP_GLUPDATE_CORE', 'TEMPGL-DIFFERENCE-FIRST');

-- اگر این Step قبلاً موفق اجرا شده، Skip کن (Restartability)
IF DMSP_LOG_PKG.is_step_completed(inpbank, inpcurrentday, 'DMSP_GLUPDATE_CORE', 'TEMPGL-DIFFERENCE-FIRST') THEN
    DMSP_LOG_PKG.log_message(inpbank, inpcurrentday, 'DMSP_GLUPDATE_CORE', 'TEMPGL-DIFFERENCE-FIRST',
                             'Skipped (already completed in previous run)', DMSP_LOG_PKG.G_INFO);
ELSE
    SAVEPOINT sp_step7;
    BEGIN
        -- منطق اصلی Step ...
        DMSP_LOG_PKG.log_step_end(inpbank, inpcurrentday, 'DMSP_GLUPDATE_CORE', 
                                  'TEMPGL-DIFFERENCE-FIRST', SQL%ROWCOUNT);
        DMSP_LOG_PKG.save_checkpoint(inpbank, inpcurrentday, 'DMSP_GLUPDATE_CORE', 
                                     'TEMPGL-DIFFERENCE-FIRST', SQL%ROWCOUNT);
    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK TO sp_step7;
            DMSP_LOG_PKG.log_error(inpbank, inpcurrentday, 'DMSP_GLUPDATE_CORE',
                                   'TEMPGL-DIFFERENCE-FIRST');
            outresult  := -1;
            outmessage := 'Step 7 failed: '||SUBSTR(SQLERRM,1,200);
            RETURN;
    END;
END IF;
```

<div dir="rtl">

**چرا:**  
بعد از این تغییر، هنگام بروز خطا، با یک Query می‌بینید **دقیقاً Step ۷** خطا داده، با چه پارامتری، با چه Backtrace، در چه ساعت. زمان دیباگ از ساعت‌ها به دقایق می‌رسد.

</div>

<div dir="rtl">

**زمان:** ۳ روز کاری  
**معیار پذیرش:**  
- ۱۲ رکورد `STARTED` و ۱۲ رکورد `COMPLETED` در `DAYEND_STEPLOG` به‌ازای هر اجرای موفق.
- در صورت خطای ساختگی در Step ۷، فقط یک رکورد `FAILED` با Backtrace کامل ثبت شود.

</div>

---

<div dir="rtl">

### مرحلهٔ ۸ — افزودن Pre-Check و Post-Check

</div>

<div dir="rtl">

**چه می‌کنیم:**  
دو پروسیجر جدید می‌سازیم:

</div>

```sql
PROCEDURE DMSP_GLUPDATE_CORE_PRECHECK(
    inpbank        IN VARCHAR2,
    inpcurrentday  IN DATE,
    outresult      OUT INTEGER,
    outmessage     OUT VARCHAR2
);

PROCEDURE DMSP_GLUPDATE_CORE_POSTCHECK(
    inpbank        IN VARCHAR2,
    inpcurrentday  IN DATE,
    outresult      OUT INTEGER,
    outmessage     OUT VARCHAR2
);
```

<div dir="rtl">

محتوای پیشنهادی Pre-Check:
- چک ۱: `BRANCHPARAMETERS.CURRENTDAY = inpcurrentday`
- چک ۲: تعداد ارزها در `CURRENCIES` با `CURRENCYWISEGL` همخوانی دارد
- چک ۳: ۰ تراکنش بدون `CURRENCYWISEGL` برای آن ارز
- چک ۴: `DATAMATE_TBS` ≥ ۱۵٪ آزاد
- چک ۵: `glaccountbalancetmp` خالی است یا فقط رکوردهای روز جاری دارد
- چک ۶: هیچ Lock فعال روی `GLACCOUNTBALANCE` و `GENERALLEDGER` نیست (برای Sessionهای دیگر)

</div>

<div dir="rtl">

محتوای پیشنهادی Post-Check:
- چک ۱: Trial Balance بانک تالی است (مجموع Debit = مجموع Credit)
- چک ۲: تعداد رکوردهای `GLACCOUNTBALANCE` با تعداد حساب‌های فعال هم‌خوانی دارد
- چک ۳: هیچ ستون NULL در فیلدهای حیاتی نیست
- چک ۴: تعداد رکوردهای `ERR$_GLACCOUNTBALANCE` با اجرای فعلی ۰ است

</div>

<div dir="rtl">

**چرا:**  
این چک‌ها در ۱۰–۳۰ ثانیه اجرا می‌شوند ولی **اگر در پروسیجر ۳۰ دقیقه‌ای خطا رخ دهد، شما ۳۰ دقیقه را هدر داده‌اید**. Pre-Check این هدررفت را حذف می‌کند.

</div>

<div dir="rtl">

**زمان:** ۱.۵ روز کاری  
**معیار پذیرش:** Pre-Check روی یک محیط با داده ناسالم، خطا را قبل از DML اصلی شناسایی کند.

</div>

---

<div dir="rtl">

## فاز ۲ — Restartability و Decomposition (۱ تا ۲ هفته)

</div>

<div dir="rtl">

### مرحلهٔ ۹ — Idempotent کردن DML ها

</div>

<div dir="rtl">

**چه می‌کنیم:**  
همهٔ `INSERT INTO ... VALUES` و `INSERT INTO ... SELECT` که ممکن است دو بار اجرا شوند به `MERGE` تبدیل می‌شوند.

</div>

<div dir="rtl">

نمونهٔ تبدیل (خط ۱۱۸۶–۱۲۵۲):

</div>

```sql
-- قبل (موجود):
IF SQL%NOTFOUND THEN
    INSERT INTO GLACCOUNTBALANCE (bank, branch, ...) VALUES (...);
END IF;

-- بعد (Idempotent):
MERGE INTO GLACCOUNTBALANCE TGT
USING (SELECT inpbank bank, j1.branch, ..., j1.openingbalance FROM dual) SRC
ON    (TGT.bank        = SRC.bank
   AND TGT.accountisn  = SRC.accountisn
   AND TGT.gldate      = SRC.gldate)
WHEN MATCHED THEN
   UPDATE SET TGT.openingbalance = SRC.openingbalance, ...
WHEN NOT MATCHED THEN
   INSERT (TGT.bank, TGT.branch, ...) VALUES (SRC.bank, SRC.branch, ...);
```

<div dir="rtl">

**چرا:**  
- اگر در Step ۴ خطا داد و Step ۳ Commit شده بود، Re-run بدون MERGE باعث Duplicate Key می‌شود.
- MERGE سریع‌تر از `IF SQL%NOTFOUND` است (یک عبور به‌جای دو عبور).

</div>

<div dir="rtl">

**زمان:** ۲ روز کاری  
**معیار پذیرش:** Re-run کامل پروسیجر روی همان داده، خروجی یکسان تولید کند.

</div>

---

<div dir="rtl">

### مرحلهٔ ۱۰ — Decompose `DMSP_GLUPDATE_CORE` به ۸–۱۲ پروسیجر کوچک‌تر

</div>

<div dir="rtl">

**چه می‌کنیم:**  
هر یک از ۱۲ Step مرحله ۷ به یک پروسیجر مستقل تبدیل می‌شود. خود `DMSP_GLUPDATE_CORE` به یک Wrapper تبدیل می‌شود که Stepها را صدا می‌زند.

</div>

```sql
CREATE OR REPLACE PROCEDURE DMSP_GLUPDATE_CORE(...) AS
BEGIN
    DBMS_APPLICATION_INFO.SET_MODULE('DMSP_GLUPDATE_CORE', 'WRAPPER');

    DMSP_GLUPDATE_PRECHECK    (inpbank, inpcurrentday, outresult, outmessage);
    IF outresult != 0 THEN RETURN; END IF;

    DMSP_GLUPDATE_INIT_PARAMS (inpbank, inpcurrentday, outresult, outmessage);
    IF outresult != 0 THEN RETURN; END IF;

    DMSP_GLUPDATE_YEAREND_INS (inpbank, inpcurrentday, outresult, outmessage);
    IF outresult != 0 THEN RETURN; END IF;

    -- ... 8–12 مرحله ...

    DMSP_GLUPDATE_POSTCHECK   (inpbank, inpcurrentday, outresult, outmessage);
END;
/
```

<div dir="rtl">

**چرا:**  
- **اجرای جداگانهٔ هر Step**: اگر Step ۷ شکست خورد و آن را دستی اصلاح کردید، می‌توانید فقط `EXEC DMSP_GLUPDATE_TEMPGL_DIFF_FIRST(...)` را اجرا کنید بدون Re-run کل پروسیجر.
- **تست‌پذیری**: هر پروسیجر کوچک‌تر تست واحد می‌گیرد.
- **Code Review**: کاهش حجم از ۳۵۹۱ خط به ~۳۰۰ خط در هر پروسیجر.
- **پروفایلینگ**: Oracle می‌تواند آمار جداگانه برای هر پروسیجر بدهد (`DBA_HIST_SQLSTAT`).

</div>

<div dir="rtl">

**زمان:** ۳ روز کاری (با احتیاط)  
**معیار پذیرش:**  
- خروجی پروسیجر Wrapper جدید با پروسیجر فعلی ۱۰۰٪ مشابه.
- اجرای پروسیجرهای کوچک‌تر به‌صورت جداگانه ممکن است.

</div>

---

<div dir="rtl">

### مرحلهٔ ۱۱ — تنظیم Watchdog Process

</div>

<div dir="rtl">

**چه می‌کنیم:**  
یک پروسیجر `DMSP_EOD_WATCHDOG` می‌سازیم که هر ۳۰ ثانیه اجرا می‌شود و Anomaliesها را تشخیص می‌دهد.

</div>

```sql
CREATE OR REPLACE PROCEDURE DMSP_EOD_WATCHDOG AS
   v_running_minutes NUMBER;
   v_blocked_count   NUMBER;
   v_proc_name       VARCHAR2(60);
BEGIN
   -- چک ۱: آیا Step ای بیش از ۱.۵ برابر متوسط تاریخی طول کشیده؟
   FOR rec IN (
      SELECT s.PROC_NAME, s.STEP_NAME, 
             ROUND((SYSTIMESTAMP - s.STARTED_AT) * 24*60, 1) RUNNING_MIN,
             AVG(h.DURATION_SEC)/60 AVG_MIN
      FROM   DAYEND_STEPLOG s, DAYEND_STEPLOG h
      WHERE  s.STEP_STATUS = 'STARTED'
        AND  s.STARTED_AT > SYSTIMESTAMP - INTERVAL '1' DAY
        AND  h.PROC_NAME = s.PROC_NAME AND h.STEP_NAME = s.STEP_NAME
        AND  h.STEP_STATUS = 'COMPLETED'
        AND  h.STARTED_AT > SYSTIMESTAMP - INTERVAL '30' DAY
      GROUP BY s.PROC_NAME, s.STEP_NAME, s.STARTED_AT
      HAVING ROUND((SYSTIMESTAMP - s.STARTED_AT) * 24*60, 1) > AVG(h.DURATION_SEC)/60 * 1.5
   ) LOOP
      DMSP_LOG_PKG.log_message(NULL, NULL, rec.PROC_NAME, rec.STEP_NAME,
         'WATCHDOG: Step running '||rec.RUNNING_MIN||' min, avg '||rec.AVG_MIN||' min',
         DMSP_LOG_PKG.G_WARN);
   END LOOP;

   -- چک ۲: آیا Session های EOD Block شده‌اند؟
   FOR rec IN (
      SELECT v.SID, v.SERIAL#, v.MODULE, v.ACTION, v.BLOCKING_SESSION, v.EVENT
      FROM   V$SESSION v
      WHERE  v.MODULE LIKE 'DMSP_%' 
        AND  v.BLOCKING_SESSION IS NOT NULL
   ) LOOP
      DMSP_LOG_PKG.log_message(NULL, NULL, rec.MODULE, rec.ACTION,
         'WATCHDOG: Session '||rec.SID||' blocked by '||rec.BLOCKING_SESSION||' on '||rec.EVENT,
         DMSP_LOG_PKG.G_WARN);
   END LOOP;

   -- چک ۳: Tablespace کم؟
   FOR rec IN (
      SELECT tablespace_name, ROUND((free_mb/total_mb)*100, 1) free_pct
      FROM (SELECT df.tablespace_name, SUM(df.bytes)/1024/1024 total_mb,
                   NVL(SUM(fs.bytes)/1024/1024, 0) free_mb
            FROM   dba_data_files df
            LEFT JOIN dba_free_space fs ON fs.tablespace_name = df.tablespace_name
            WHERE  df.tablespace_name IN ('DATAMATE_TBS','UNDOTBS1')
            GROUP BY df.tablespace_name)
      WHERE (free_mb/total_mb)*100 < 15
   ) LOOP
      DMSP_LOG_PKG.log_message(NULL, NULL, 'WATCHDOG', 'TABLESPACE',
         rec.tablespace_name||' at '||rec.free_pct||'% free',
         DMSP_LOG_PKG.G_FATAL);
   END LOOP;
END;
/

-- ثبت در DBMS_SCHEDULER برای اجرای هر ۳۰ ثانیه در طول EOD
BEGIN
   DBMS_SCHEDULER.CREATE_JOB(
      job_name        => 'DMSP_EOD_WATCHDOG_JOB',
      job_type        => 'STORED_PROCEDURE',
      job_action      => 'DMSP_EOD_WATCHDOG',
      repeat_interval => 'FREQ=SECONDLY; INTERVAL=30',
      enabled         => FALSE  -- فقط در طول EOD فعال شود
   );
END;
/
```

<div dir="rtl">

**چرا:**  
بدون Watchdog، تشخیص اینکه EOD «گیر کرده» نه «در حال پیشرفت کند است» سخت است. Watchdog این تمایز را خودکار می‌کند.

</div>

<div dir="rtl">

**زمان:** ۱ روز کاری  
**معیار پذیرش:** در شبیه‌سازی Lock، Watchdog در کمتر از ۱ دقیقه هشدار می‌دهد.

</div>

---

<div dir="rtl">

## فاز ۳ — Operations و Polish (۱ هفته)

</div>

<div dir="rtl">

### مرحلهٔ ۱۲ — راه‌اندازی Real-Time Dashboard و Alerting

</div>

<div dir="rtl">

**چه می‌کنیم:**

</div>

<div dir="rtl">

#### الف) Dashboard
از یکی از این گزینه‌ها استفاده کنید (به ترتیب اولویت برای اکوسیستم Oracle):

</div>

<div dir="rtl">

1. **Oracle APEX** (داخلی، رایگان، سریع‌ترین): یک App با ۴ صفحه:
   - صفحهٔ ۱: نمای کلی EOD امروز (Card با وضعیت)
   - صفحهٔ ۲: لیست Step ها با Status و Duration (Refresh هر ۵ ثانیه)
   - صفحهٔ ۳: Errorهای ۲۴ ساعت اخیر با Filter
   - صفحهٔ ۴: تاریخچهٔ Duration هر Step (Trend chart)

</div>

<div dir="rtl">

2. **Grafana + Oracle Plugin**: اگر Grafana برای بقیهٔ Stack دارید.

</div>

<div dir="rtl">

3. **SQL Developer Web**: ساده‌ترین گزینه — فقط View ها را Bookmark کنید.

</div>

<div dir="rtl">

#### ب) Alerting
سه کانال:

</div>

```sql
CREATE OR REPLACE PROCEDURE DMSP_EOD_ALERT(
    p_severity    IN VARCHAR2,
    p_subject     IN VARCHAR2,
    p_body        IN VARCHAR2
) AS
   PRAGMA AUTONOMOUS_TRANSACTION;
BEGIN
    -- ۱. Email (به Operations + DBA Team)
    UTL_MAIL.SEND(
        sender    => 'eod-noreply@bank.example.ir',
        recipients=> 'ops@bank.example.ir,dba@bank.example.ir',
        subject   => '['||p_severity||'] EOD: '||p_subject,
        message   => p_body
    );

    -- ۲. SMS (با استفاده از مکانیزم موجود)
    INSERT INTO PUSHMESSAGE (MOBILENUMBER, CMD_CODE, MESSEGE, SENT, ISFINANCIALTXN)
    SELECT MOBILENUMBER, 'DAYEND_ALERT', SUBSTR(p_subject||' '||p_body, 1, 160), 'N', 'Y'
    FROM   EVENTSMS WHERE DESCRIPTION = 'DAYEND'
       AND p_severity IN ('ERROR','FATAL');  -- فقط برای خطاهای جدی SMS

    -- ۳. Webhook به Slack/Teams
    DECLARE
        l_req       UTL_HTTP.req;
        l_resp      UTL_HTTP.resp;
        l_payload   VARCHAR2(4000);
    BEGIN
        l_payload := '{"text":"['||p_severity||'] '||REPLACE(p_subject,'"','''')||'\n'
                                 ||REPLACE(SUBSTR(p_body,1,500),'"','''')||'"}';
        l_req := UTL_HTTP.begin_request('https://hooks.slack.com/services/YOUR/WEBHOOK/URL', 'POST');
        UTL_HTTP.set_header(l_req, 'Content-Type', 'application/json');
        UTL_HTTP.write_text(l_req, l_payload);
        l_resp := UTL_HTTP.get_response(l_req);
        UTL_HTTP.end_response(l_resp);
    EXCEPTION
        WHEN OTHERS THEN NULL;  -- اگر Webhook fail شد، Email/SMS کفایت می‌کند
    END;

    COMMIT;
END;
/
```

<div dir="rtl">

سپس در `DMSP_LOG_PKG.log_error`، اگر `severity = FATAL`، خود به‌خود `DMSP_EOD_ALERT` صدا زده شود.

</div>

<div dir="rtl">

#### ج) Runbook
یک سند داخلی به نام `Runbook_EOD_Errors.md` بسازید با ساختار:

</div>

```markdown
# Runbook: خطاهای رایج EOD

## خطا ۱: ORA-00001 unique constraint on GLACCOUNTBALANCE_PK
علت محتمل: Re-run بدون Cleanup
رفع:  
  1. SELECT * FROM V_DAYEND_DASHBOARD; -- ببین در کدام Step خطا داده
  2. DELETE FROM glaccountbalancetmp WHERE bank=:b AND gldate=:d;
  3. DELETE FROM glaccountbalance WHERE bank=:b AND gldate=:d;
  4. EXEC DMSP_GLUPDATE_CORE(:b, :d, :r, :m);

## خطا ۲: ORA-04036 PGA memory exceeds limit
...
```

<div dir="rtl">

**زمان:** ۲ روز کاری  
**معیار پذیرش:** در یک شبیه‌سازی FATAL، Email + SMS + Webhook + Log همگی موفق ارسال شوند.

</div>

---

<div dir="rtl">

## خلاصه‌ی زمان‌بندی و اولویت

</div>

<div dir="rtl">

| فاز | مرحله | زمان | اولویت | منفعت |
|-----|-------|------|---------|--------|
| ۰ | ۱: تکمیل ساختار جداول | ۴h | 🔴 Critical | پایه برای همه چیز |
| ۰ | ۲: ساخت `DMSP_LOG_PKG` | ۸h | 🔴 Critical | پایه برای همه چیز |
| ۰ | ۳: `EXCEPTION WHEN OTHERS` در `DMSP_GLUPDATE_CORE` | ۱h | 🔴 Critical | منفعت بزرگ، هزینهٔ کم |
| ۰ | ۴: اصلاح Trigger | ۱h+۲h test | 🔴 Critical | حفظ Context |
| ۰ | ۵: ساخت View داشبورد | ۲h | 🔴 Critical | دیداری |
| ۱ | ۶: `DBMS_APPLICATION_INFO` در ۵۴ پروسیجر | ۲ روز | 🟠 High | Real-time visibility |
| ۱ | ۷: تقسیم به ۱۲ Step منطقی | ۳ روز | 🟠 High | Forensics دقیق |
| ۱ | ۸: Pre-Check و Post-Check | ۱.۵ روز | 🟠 High | کشف زودهنگام |
| ۲ | ۹: Idempotent کردن DML | ۲ روز | 🟡 Medium | Re-run بدون درد |
| ۲ | ۱۰: Decompose به پروسیجرهای کوچک‌تر | ۳ روز | 🟡 Medium | تست‌پذیری، نگه‌داری |
| ۲ | ۱۱: Watchdog | ۱ روز | 🟡 Medium | تشخیص Stuck |
| ۳ | ۱۲: Dashboard + Alerting + Runbook | ۲ روز | 🟢 Low | Polish |

</div>

<div dir="rtl">

**جمع کل: ~۶ هفته نفر-کار** (می‌تواند ۲–۳ هفته با ۲ نفر موازی فشرده شود)

</div>

<div dir="rtl">

**Quick-Win فاز ۰: ~۲ روز کاری برای ۶۰٪ منفعت.**

</div>

---

<div dir="rtl">

## معیارهای موفقیت پروژه (Success Metrics)

</div>

<div dir="rtl">

پس از پیاده‌سازی کامل، این KPI ها باید تغییر کنند:

</div>

<div dir="rtl">

| KPI | قبل | هدف بعد |
|-----|-----|----------|
| MTTR (میانگین زمان رفع خطا) | ۲–۸ ساعت | ۱۰–۳۰ دقیقه |
| % از خطاها که Pre-Check قبل از DML کشف می‌کند | ۰٪ | ≥ ۸۰٪ |
| % از خطاها که با Re-run خودکار رفع می‌شوند | ۰٪ | ≥ ۲۰٪ |
| میانگین زمان EOD کامل | (Baseline) | ≤ ۱.۱۵× Baseline (overhead کم) |
| % از پروسیجرها با Step-Logging | < ۵٪ | ۱۰۰٪ |
| % از پروسیجرها که Idempotent اند | < ۵۰٪ | ≥ ۹۵٪ |
| تعداد Alert جعلی (False Positives) در روز | (Baseline) | ≤ ۲ |
| زمان بازیابی Context پس از خطا | ۳۰–۶۰ دقیقه | ≤ ۱ دقیقه |

</div>

---

<div dir="rtl">

## ریسک‌ها و راه کاهش

</div>

<div dir="rtl">

| ریسک | احتمال | تأثیر | راه کاهش |
|------|---------|--------|-----------|
| Logging سربار اضافه می‌کند | متوسط | کم | از `PRAGMA AUTONOMOUS_TRANSACTION` استفاده می‌شود؛ Index درست؛ تست بنچمارک |
| Refactor باعث Bug رگرسیون می‌شود | بالا | بالا | Test Plan کامل: Diff خروجی پروسیجر فعلی vs Refactored روی Production-like data |
| Trigger های جدید روی Performance اثر می‌گذارند | کم | متوسط | Trigger ها فقط روی UPDATE یک ستون خاص؛ بنچمارک قبل/بعد |
| تیم Operations الگوی جدید را یاد نگیرد | متوسط | متوسط | Runbook، آموزش ۲ ساعته، Drill (شبیه‌سازی خطا) |
| فشرده شدن جداول لاگ | بالا | کم | Partition by Month + Auto-Purge بعد از ۹۰ روز |

</div>

---

<div dir="rtl">

## گام بعدی

</div>

<div dir="rtl">

اگر این طرح قابل قبول است، پیشنهاد می‌کنم با **مرحلهٔ ۱ تا ۵ (Quick-Wins فاز ۰)** شروع کنید. این ۵ مرحله را در یک Sprint یک‌هفته‌ای روی Test پیاده کنید، خروجی روی یک EOD آزمایشی تست کنید، و سپس به‌صورت روزشمار در Production فعال کنید.

</div>

<div dir="rtl">

برای جزئیات کد PL/SQL هر مرحله، فایل `03_refactored_procedure_template.md` را ببینید.
برای SQL های مانیتورینگ و Forensics آماده‌برای‌اجرا، فایل `04_diagnostic_toolkit.md` را ببینید.

</div>

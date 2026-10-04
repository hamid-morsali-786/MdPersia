<div dir="rtl">

# راهنمای جامع عیب‌یابی و مدیریت خطای فرایند پایان روز (EOD)
## سیستم بانکی DataMate - Oracle 19c

---

> **نسخه:** 1.0  
> **تاریخ:** خرداد ۱۴۰۵  
> **هدف:** ارائه دستورالعمل‌ها، چک‌لیست‌ها و کوئری‌های تشخیصی برای شناسایی سریع، رفع خطا و ادامه فرایند پایان روز در کمترین زمان ممکن

---

## فهرست مطالب

1. [معماری و نقشه کلی فرایند EOD](#1-معماری-و-نقشه-کلی-فرایند-eod)
2. [جداول لاگ و مانیتورینگ](#2-جداول-لاگ-و-مانیتورینگ)
3. [چک‌لیست پیش از شروع EOD (Pre-EOD Health Check)](#3-چک-لیست-پیش-از-شروع-eod)
4. [مانیتورینگ حین اجرای EOD (Real-Time Monitoring)](#4-مانیتورینگ-حین-اجرای-eod)
5. [تشخیص خطا: فلوچارت تصمیم‌گیری](#5-تشخیص-خطا-فلوچارت-تصمیم-گیری)
6. [سناریوهای خطای رایج و راه‌حل‌ها](#6-سناریوهای-خطای-رایج)
   - 6.1 [Row Lock / Enqueue Wait](#61-row-lock--enqueue-wait)
   - 6.2 [Numeric Overflow (ORA-06502)](#62-numeric-overflow)
   - 6.3 [Deadlock (ORA-00060)](#63-deadlock)
   - 6.4 [Timeout / Long Running](#64-timeout--long-running)
   - 6.5 [Data Integrity / Business Logic Errors](#65-data-integrity-errors)
   - 6.6 [GL Imbalance / Trial Balance Mismatch](#66-gl-imbalance)
   - 6.7 [ORA-01555 Snapshot Too Old](#67-snapshot-too-old)
   - 6.8 [Tablespace Full / ORA-01653](#68-tablespace-full)
7. [روال ادامه (Resume) فرایند پایان روز](#7-روال-ادامه-فرایند-eod)
8. [روال اجرای دستی مراحل EOD](#8-روال-اجرای-دستی-eod)
9. [چک‌لیست پس از اتمام EOD (Post-EOD Validation)](#9-چک-لیست-پس-از-اتمام-eod)
10. [کوئری‌های تشخیصی مرجع (Quick Reference)](#10-کوئری-های-تشخیصی-مرجع)
11. [پیشنهادات بهبود (بدون تغییر ساختار)](#11-پیشنهادات-بهبود)

---

## 1. معماری و نقشه کلی فرایند EOD

### 1.1 جریان کلی اجرا

</div>

```
شروع (دکمه UI) → DMSP_DAYEND_CORE
    │
    ├── Pre-Checks (DAYENDEXEC, GLACCOUNTBALANCETMP, PRODUCTBALANCETMP)
    ├── TRUNCATE log tables / Archive to _HIST tables
    ├── INSERT 17 رکورد در DAYENDLOG (PROCSEQ 1-16 + 99)
    ├── DMSP_BEFOREEOD_CHECK (PROCSEQ=99)
    ├── ATM Offline (ATMSTATUS.GO_OFFLINE = 'Y')
    ├── BRANCHPARAMETERS.DAYENDSTARTED = 'Y'
    │
    └── DBMS_JOB.SUBMIT برای 16 جاب (همه همزمان submit می‌شوند)
        │
        ├── Jobs 1,2,3: مستقل (همزمان قابل اجرا)
        │   ├── JOB 1: DMSP_FLEXISWEEPIN_JOB       🔴 غیرفعال
        │   ├── JOB 2: DMSP_FLEXISWEEPOUT_JOB      🔴 غیرفعال
        │   └── JOB 3: DMSP_SWAPLOANANDCASA_JOB    🟢 (مهمترین - 12 پروسیجر)
        │
        ├── Jobs 4,5,6,7: وابسته به Job 3 (پس از اتمام Job 3)
        │   ├── JOB 4: DMSP_DD_JOB1 (SB Interest)  🟢
        │   ├── JOB 5: DMSP_TD_JOB1 (TD Interest)  🟢
        │   ├── JOB 6: DMSP_TL_JOB1 (Loans)        🟢
        │   └── JOB 7: DMSP_DL_JOB1 (DL)           🔴 غیرفعال
        │
        ├── Jobs 8,9,10: وابسته به Job 6
        │   ├── JOB 8: DMSP_UPDPOSTPONEDINTEREST    🟢
        │   ├── JOB 9: DMSP_CHANGESTATUSVOUCHER     🟢
        │   └── JOB 10: DMSP_TL_INTACRRUAL          🟢
        │
        ├── JOB 11: CCSP_DAYEND_JOB (وابسته به Job 10) 🟢
        │
        ├── JOB 12: DMSP_GL_JOB1 (وابسته به همه قبلی) 🟢 ⭐ بحرانی
        │   └── شامل DMSP_GLUPDATE_CORE (طولانی‌ترین پروسیجر)
        │
        ├── JOB 13: DMSP_UPDATEACCOUNTMASTER        🟢
        ├── JOB 14: DMSP_COMMONUPDATE               🔴 غیرفعال
        ├── JOB 15: DMSP_COMMPROCFORALL              🟢
        └── JOB 16: DMSP_UPDDAYEND_JOB (پایان رسمی) 🟢
```

<div dir="rtl">

### 1.2 نکات کلیدی معماری

- **مکانیزم اجرا:** تمام 16 جاب با `DBMS_JOB.SUBMIT` همزمان ارسال می‌شوند، اما هر جاب داخلاً منتظر اتمام جاب‌های وابسته‌اش می‌ماند (با بررسی `EXECUTIONSTARTED` در `DAYENDLOG`).
- **مکانیزم Resume:** پس از خطا و رفع آن، با زدن مجدد دکمه شروع، سیستم از جایی که `EXECUTIONFAILED='Y'` است ادامه می‌دهد.
- **محدودیت زمانی:** کمتر از ۳ ساعت (00:10 تا حداکثر 03:10)

---

## 2. جداول لاگ و مانیتورینگ

### 2.1 DAYENDEXEC
وجود رکورد = فرایند در حال اجرا. حذف رکورد = خطا رخ داده یا فرایند تمام شده.

### 2.2 DAYENDLOG (17 رکورد اصلی)

| فیلد | توضیح |
|---|---|
| `PROCSEQ` | ترتیب جاب (1-16 و 99) |
| `PROCNAME` | نام جاب |
| `EXECUTIONFLAG` | Y = سشن دریافت شده |
| `EXECUTIONSTARTED` | Y = اجرا شروع شده |
| `EXECUTIONFAILED` | Y = خطا رخ داده |

### 2.3 DAYEND_JOBLOG_TABLE (جزئیات پروسیجرها)

| فیلد | توضیح |
|---|---|
| `JOB_ID` | شناسه جاب |
| `START_TIME` / `END_TIME` | زمان شروع و پایان |
| `JOBNAME` | نام جاب والد |
| `PROCEDURENAME` | نام پروسیجر اجرا شده |
| `EXECUTIONFLAG` | Y = اجرا شده |
| `EXECUTIONFAILED` | Y = خطا |

### 2.4 DAYEND_PROCLOG_TABLE (پیام‌های خطا)

| فیلد | توضیح |
|---|---|
| `SEQ_ID` | شناسه ترتیبی |
| `ERRORCODE` | 0 = موفق، -1 = خطا |
| `ERRORMSG` | متن پیام/خطا |
| `PROCEDURENAME` | نام پروسیجر |

---

## 3. چک‌لیست پیش از شروع EOD

### ✅ Pre-EOD Health Check Checklist

**هدف:** جلوگیری از خطاهای قابل پیش‌بینی قبل از شروع فرایند

#### 3.1 بررسی سشن‌های فعال و لاک‌ها

</div>

```sql
-- Q01: بررسی وجود لاک روی جداول حساس EOD
-- اگر نتیجه‌ای برگشت، باید قبل از شروع EOD رفع شوند
SELECT 
    s.sid,
    s.serial#,
    s.username,
    s.program,
    s.machine,
    s.status,
    o.object_name,
    o.object_type,
    l.locked_mode,
    DECODE(l.locked_mode, 
           1, 'NULL', 2, 'ROW-S (SS)', 3, 'ROW-X (SX)', 
           4, 'SHARE (S)', 5, 'S/ROW-X (SSX)', 6, 'EXCLUSIVE (X)') lock_type,
    s.sql_id,
    s.last_call_et AS seconds_in_wait
FROM v$locked_object l
JOIN dba_objects o ON l.object_id = o.object_id
JOIN v$session s ON l.session_id = s.sid
WHERE o.object_name IN (
    'ACCOUNTMASTER', 'GENERALLEDGER', 'GLACCOUNTBALANCETMP', 
    'GLACCOUNTBALANCE', 'TRANSACTIONS', 'TERMLOANSDATA',
    'DAYENDLOG', 'DAYENDEXEC', 'BRANCHPARAMETERS',
    'PRODUCTBALANCETMP', 'SBINTACCRUALHIST', 'TRANSFERHEADER',
    'TRANSFERDETAILS', 'NPAHISTORY', 'SCHEMEDEFINITIONS'
)
ORDER BY o.object_name, s.last_call_et DESC;
```

```sql
-- Q02: بررسی سشن‌های برنامه‌های دیگر که ممکن است تداخل ایجاد کنند
SELECT 
    s.sid, s.serial#, s.username, s.program, s.machine,
    s.status, s.logon_time, s.last_call_et,
    (SELECT sql_text FROM v$sql WHERE sql_id = s.sql_id AND ROWNUM = 1) current_sql
FROM v$session s
WHERE s.type = 'USER'
  AND s.username = 'DATAMATE'
  AND s.program NOT LIKE '%TOAD%'
  AND s.program NOT LIKE '%SQL Developer%'
  AND s.program NOT LIKE '%sqlplus%'
ORDER BY s.last_call_et DESC;
```

<div dir="rtl">

#### 3.2 بررسی وضعیت دیتابیس

</div>

```sql
-- Q03: بررسی فضای Tablespace ها
SELECT 
    tablespace_name,
    ROUND(used_space_mb, 2) used_mb,
    ROUND(free_space_mb, 2) free_mb,
    ROUND(total_space_mb, 2) total_mb,
    ROUND((used_space_mb / total_space_mb) * 100, 1) pct_used
FROM (
    SELECT 
        a.tablespace_name,
        a.bytes / 1024 / 1024 total_space_mb,
        a.bytes / 1024 / 1024 - NVL(b.free_mb, 0) used_space_mb,
        NVL(b.free_mb, 0) free_space_mb
    FROM (
        SELECT tablespace_name, SUM(bytes) bytes
        FROM dba_data_files GROUP BY tablespace_name
    ) a
    LEFT JOIN (
        SELECT tablespace_name, SUM(bytes) / 1024 / 1024 free_mb
        FROM dba_free_space GROUP BY tablespace_name
    ) b ON a.tablespace_name = b.tablespace_name
)
WHERE ROUND((used_space_mb / total_space_mb) * 100, 1) > 80
ORDER BY pct_used DESC;
```

```sql
-- Q04: بررسی وضعیت UNDO Tablespace (جلوگیری از ORA-01555)
SELECT 
    tablespace_name,
    ROUND(SUM(bytes) / 1024 / 1024, 2) total_mb,
    ROUND(SUM(DECODE(status, 'ACTIVE', bytes, 0)) / 1024 / 1024, 2) active_mb,
    ROUND(SUM(DECODE(status, 'UNEXPIRED', bytes, 0)) / 1024 / 1024, 2) unexpired_mb,
    ROUND(SUM(DECODE(status, 'EXPIRED', bytes, 0)) / 1024 / 1024, 2) expired_mb
FROM dba_undo_extents
GROUP BY tablespace_name;
```

<div dir="rtl">

#### 3.3 بررسی پیش‌نیازهای داده‌ای

</div>

```sql
-- Q05: بررسی خالی بودن DAYENDEXEC (اگر رکوردی هست یعنی EOD قبلی ناتمام است)
SELECT COUNT(*) AS dayendexec_count FROM DATAMATE.DAYENDEXEC;

-- Q06: بررسی انتقال GLACCOUNTBALANCETMP از روز قبل
SELECT COUNT(*) AS stale_gl_records 
FROM DATAMATE.GLACCOUNTBALANCETMP 
WHERE GLDATE < (SELECT CURRENTDAY FROM DATAMATE.BRANCHPARAMETERS WHERE ISDATACENTRE = 'Y');

-- Q07: بررسی انتقال PRODUCTBALANCETMP از روز قبل
SELECT COUNT(*) AS stale_prod_records 
FROM DATAMATE.PRODUCTBALANCETMP 
WHERE PRODUCTDATE < (SELECT CURRENTDAY FROM DATAMATE.BRANCHPARAMETERS WHERE ISDATACENTRE = 'Y');

-- Q08: بررسی وضعیت شعب (READYFORDAYEND)
SELECT BRANCH, NETWORKED, READYFORDAYEND, DAYENDSTARTED, DAYENDCOMPLETED, CURRENTDAY
FROM DATAMATE.BRANCHPARAMETERS
WHERE NETWORKED = 'Y'
ORDER BY BRANCH;

-- Q09: بررسی تاریخ DATACENTRE
SELECT BRANCH, CURRENTDAY, PREVIOUSDAY, YEARENDDATE, ISDATACENTRE
FROM DATAMATE.BRANCHPARAMETERS
WHERE ISDATACENTRE = 'Y';
```

<div dir="rtl">

#### 3.4 بررسی DBMS_JOB

</div>

```sql
-- Q10: بررسی جاب‌های متوقف یا broken
SELECT job, what, broken, failures, last_date, next_date, interval
FROM dba_jobs
WHERE broken = 'Y' OR failures > 0;

-- Q11: بررسی جاب‌های در حال اجرا
SELECT j.job, j.what, r.sid, r.failures
FROM dba_jobs_running r
JOIN dba_jobs j ON r.job = j.job;
```

<div dir="rtl">

---

## 4. مانیتورینگ حین اجرای EOD

### 4.1 داشبورد وضعیت کلی EOD (اجرای هر ۳۰ ثانیه)

</div>

```sql
-- Q12: داشبورد اصلی - وضعیت همه جاب‌ها
SELECT 
    PROCSEQ,
    PROCNAME,
    EXECUTIONFLAG AS "سشن دریافت",
    EXECUTIONSTARTED AS "شروع شده",
    EXECUTIONFAILED AS "خطا",
    CASE 
        WHEN EXECUTIONFAILED = 'Y' THEN '❌ خطا - نیاز به بررسی'
        WHEN EXECUTIONSTARTED = 'Y' AND EXECUTIONFLAG = 'Y' THEN '✅ تمام شده'
        WHEN EXECUTIONFLAG = 'Y' AND EXECUTIONSTARTED = 'N' THEN '⏳ در انتظار وابستگی‌ها'
        WHEN EXECUTIONFLAG = 'N' THEN '⬜ شروع نشده'
        ELSE '🔄 در حال اجرا'
    END AS status_desc
FROM DATAMATE.DAYENDLOG
ORDER BY PROCSEQ;
```

```sql
-- Q13: آخرین پروسیجر اجرا شده و زمان‌بندی
SELECT 
    PROCEDURENAME,
    TO_CHAR(START_TIME, 'HH24:MI:SS') start_time,
    TO_CHAR(END_TIME, 'HH24:MI:SS') end_time,
    ROUND((END_TIME - START_TIME) * 24 * 60, 1) AS duration_min,
    EXECUTIONFLAG,
    EXECUTIONFAILED
FROM DATAMATE.DAYEND_JOBLOG_TABLE
ORDER BY START_TIME DESC
FETCH FIRST 20 ROWS ONLY;
```

```sql
-- Q14: بررسی خطاها در PROCLOG
SELECT 
    SEQ_ID,
    TO_CHAR(START_TIME, 'HH24:MI:SS') start_time,
    TO_CHAR(END_TIME, 'HH24:MI:SS') end_time,
    ERRORCODE,
    ERRORMSG,
    PROCEDURENAME
FROM DATAMATE.DAYEND_PROCLOG_TABLE
WHERE ERRORCODE <> 0
ORDER BY SEQ_ID DESC;
```

<div dir="rtl">

### 4.2 مانیتورینگ لاک‌ها حین EOD

</div>

```sql
-- Q15: مانیتورینگ لحظه‌ای لاک‌ها روی جداول بحرانی حین EOD
SELECT 
    s.sid,
    s.serial#,
    s.username,
    s.program,
    o.object_name,
    DECODE(l.locked_mode, 
           1,'NULL', 2,'ROW-S', 3,'ROW-X', 
           4,'SHARE', 5,'S/ROW-X', 6,'EXCLUSIVE') lock_mode,
    s.last_call_et AS wait_seconds,
    s.sql_id,
    (SELECT SUBSTR(sql_text,1,200) FROM v$sql WHERE sql_id = s.sql_id AND ROWNUM = 1) sql_text
FROM v$locked_object l
JOIN dba_objects o ON l.object_id = o.object_id
JOIN v$session s ON l.session_id = s.sid
WHERE o.object_name IN ('ACCOUNTMASTER', 'GENERALLEDGER', 'GLACCOUNTBALANCETMP',
                         'GLACCOUNTBALANCE', 'TRANSACTIONS', 'TERMLOANSDATA')
ORDER BY s.last_call_et DESC;
```

```sql
-- Q16: شناسایی Blocking Sessions (سشن‌هایی که جلوی EOD را گرفته‌اند)
SELECT 
    'BLOCKER' AS role,
    s1.sid AS blocker_sid,
    s1.serial# AS blocker_serial,
    s1.username AS blocker_user,
    s1.program AS blocker_program,
    s1.machine AS blocker_machine,
    s1.status AS blocker_status,
    s1.sql_id AS blocker_sql_id,
    s1.last_call_et AS blocker_wait_sec,
    '→ blocks →' AS direction,
    s2.sid AS blocked_sid,
    s2.username AS blocked_user,
    s2.program AS blocked_program,
    s2.event AS blocked_event
FROM v$session s1
JOIN v$session s2 ON s1.sid = s2.blocking_session
WHERE s2.blocking_session IS NOT NULL
ORDER BY s1.last_call_et DESC;
```

```sql
-- Q17: Wait Events مرتبط با EOD
SELECT 
    s.sid, s.serial#, s.username, s.program,
    s.event,
    s.seconds_in_wait,
    s.state,
    s.sql_id,
    (SELECT SUBSTR(sql_text,1,200) FROM v$sql WHERE sql_id = s.sql_id AND ROWNUM = 1) sql_preview
FROM v$session s
WHERE s.username = 'DATAMATE'
  AND s.status = 'ACTIVE'
  AND s.event NOT LIKE 'SQL*Net%'
  AND s.event NOT LIKE 'rdbms ipc%'
ORDER BY s.seconds_in_wait DESC;
```

<div dir="rtl">

### 4.3 مانیتورینگ عملکرد (Performance)

</div>

```sql
-- Q18: Long Operations - پیشرفت عملیات طولانی
SELECT 
    sid, serial#, opname,
    ROUND(sofar / totalwork * 100, 1) pct_complete,
    sofar, totalwork,
    ROUND(elapsed_seconds / 60, 1) elapsed_min,
    ROUND(time_remaining / 60, 1) remaining_min,
    message
FROM v$session_longops
WHERE sofar < totalwork
  AND totalwork > 0
ORDER BY start_time DESC;
```

```sql
-- Q19: بزرگترین کوئری‌های فعال (مرتبط با EOD)
SELECT 
    s.sid, s.serial#,
    sq.sql_id,
    sq.executions,
    ROUND(sq.elapsed_time / 1000000, 1) elapsed_sec,
    ROUND(sq.buffer_gets / GREATEST(sq.executions, 1)) avg_buffer_gets,
    SUBSTR(sq.sql_text, 1, 300) sql_text
FROM v$session s
JOIN v$sql sq ON s.sql_id = sq.sql_id
WHERE s.username = 'DATAMATE'
  AND s.status = 'ACTIVE'
ORDER BY sq.elapsed_time DESC
FETCH FIRST 10 ROWS ONLY;
```

<div dir="rtl">

---

## 5. تشخیص خطا: فلوچارت تصمیم‌گیری

### مرحله ۱: شناسایی جاب خطادار

</div>

```sql
-- Q20: پیدا کردن جاب(های) خطادار
SELECT PROCSEQ, PROCNAME, EXECUTIONFAILED
FROM DATAMATE.DAYENDLOG
WHERE EXECUTIONFAILED = 'Y';
```

<div dir="rtl">

### مرحله ۲: شناسایی پروسیجر خطادار

</div>

```sql
-- Q21: پیدا کردن پروسیجر خطادار با جزئیات
SELECT 
    j.PROCEDURENAME,
    j.JOBNAME,
    TO_CHAR(j.START_TIME, 'YYYY/MM/DD HH24:MI:SS') start_time,
    TO_CHAR(j.END_TIME, 'YYYY/MM/DD HH24:MI:SS') end_time,
    j.EXECUTIONFAILED,
    p.ERRORCODE,
    p.ERRORMSG
FROM DATAMATE.DAYEND_JOBLOG_TABLE j
LEFT JOIN DATAMATE.DAYEND_PROCLOG_TABLE p 
    ON j.PROCEDURENAME = p.PROCEDURENAME
WHERE j.EXECUTIONFAILED = 'Y'
   OR p.ERRORCODE <> 0
ORDER BY j.START_TIME DESC;
```

<div dir="rtl">

### مرحله ۳: دسته‌بندی نوع خطا

| شناسه خطا | نوع خطا | ارجاع به بخش |
|---|---|---|
| `ORA-00054` / `enq: TX - row lock contention` | Row Lock | بخش 6.1 |
| `ORA-06502` / `numeric or value error` | Numeric Overflow | بخش 6.2 |
| `ORA-00060` | Deadlock | بخش 6.3 |
| عدم پایان پروسیجر در زمان معقول | Timeout | بخش 6.4 |
| خطای کسب‌وکاری (ERRORCODE = -1) | Business Logic | بخش 6.5 |
| `Trial Balance not tallied` / GL Mismatch | GL Imbalance | بخش 6.6 |
| `ORA-01555` | Snapshot Too Old | بخش 6.7 |
| `ORA-01653` / `ORA-01654` | Tablespace Full | بخش 6.8 |

---

## 6. سناریوهای خطای رایج

### 6.1 Row Lock / Enqueue Wait

#### توضیح مشکل
رکوردهای جدول `ACCOUNTMASTER` (یا سایر جداول بحرانی) توسط سشن‌های برنامه‌های دیگر قفل شده‌اند و پروسیجرهای EOD که نیاز به UPDATE این رکوردها دارند (مانند محاسبه سود سپرده‌ها) نمی‌توانند ادامه دهند.

#### پروسیجرهای آسیب‌پذیر
- `DMSP_DAYENDSBINTACCRUAL_CORE` (سود سپرده SB - UPDATE ACCOUNTMASTER)
- `DMSP_TDINTACCRUAL_CORE` (سود سپرده TD - UPDATE ACCOUNTMASTER)
- `DMSP_UPDATEACCOUNTMASTER_CORE` (آپدیت کلی ACCOUNTMASTER)
- `DMSP_GLUPDATE_CORE` (UPDATE GENERALLEDGER, GLACCOUNTBALANCE)
- `DMSP_TLDAYEND_UPD_CORE` (UPDATE TERMLOANSDATA, ACCOUNTMASTER)

#### مرحله ۱: تشخیص

</div>

```sql
-- Q22: شناسایی دقیق رکوردهای لاک شده ACCOUNTMASTER
SELECT 
    s.sid blocker_sid,
    s.serial# blocker_serial,
    s.username,
    s.program,
    s.machine,
    s.status,
    s.last_call_et wait_sec,
    s.sql_id,
    (SELECT SUBSTR(sql_text,1,300) FROM v$sql WHERE sql_id = s.sql_id AND ROWNUM = 1) sql_text,
    DBMS_ROWID.ROWID_OBJECT(l.ROW_WAIT_OBJ#) obj_id,
    o.object_name
FROM v$session s
JOIN v$locked_object lo ON s.sid = lo.session_id
JOIN dba_objects o ON lo.object_id = o.object_id
LEFT JOIN v$lock l ON s.sid = l.sid AND l.type = 'TX'
WHERE o.object_name = 'ACCOUNTMASTER'
  AND lo.locked_mode >= 3  -- ROW-X or higher
ORDER BY s.last_call_et DESC;
```

```sql
-- Q23: شناسایی زنجیره Blocking (چه کسی جلوی چه کسی را گرفته)
SELECT 
    LEVEL,
    LPAD(' ', 2*(LEVEL-1)) || s.sid || ' (' || s.username || ' / ' || s.program || ')' AS session_info,
    s.status,
    s.event,
    s.seconds_in_wait,
    s.sql_id,
    CASE WHEN s.blocking_session IS NULL THEN '>>> ROOT BLOCKER <<<' ELSE '' END AS is_root
FROM v$session s
WHERE s.blocking_session IS NOT NULL OR s.sid IN (SELECT blocking_session FROM v$session WHERE blocking_session IS NOT NULL)
START WITH s.blocking_session IS NULL 
  AND s.sid IN (SELECT blocking_session FROM v$session WHERE blocking_session IS NOT NULL)
CONNECT BY PRIOR s.sid = s.blocking_session;
```

<div dir="rtl">

#### مرحله ۲: تصمیم‌گیری

| وضعیت | اقدام |
|---|---|
| سشن blocker مربوط به برنامه دیگر است و IDLE است | Kill Session |
| سشن blocker مربوط به برنامه دیگر و ACTIVE است | ابتدا متوقف کردن برنامه، سپس Kill |
| سشن blocker مربوط به خود EOD است | احتمال Deadlock → بخش 6.3 |

#### مرحله ۳: Kill Session

</div>

```sql
-- Q24: Kill سشن مسدودکننده (SID و SERIAL# را از کوئری Q22/Q23 بگذارید)
-- ⚠️ هشدار: ابتدا مطمئن شوید سشن مربوط به EOD نیست
ALTER SYSTEM KILL SESSION 'SID,SERIAL#' IMMEDIATE;

-- اگر Kill معمولی جواب نداد:
ALTER SYSTEM DISCONNECT SESSION 'SID,SERIAL#' IMMEDIATE;

-- برای پیدا کردن OS PID و kill از سمت سیستم‌عامل (آخرین راه):
SELECT s.sid, s.serial#, p.spid AS os_pid, s.program
FROM v$session s JOIN v$process p ON s.paddr = p.addr
WHERE s.sid = &blocker_sid;
-- سپس در سیستم‌عامل: kill -9 <os_pid>
```

<div dir="rtl">

#### مرحله ۴: بررسی و ادامه

</div>

```sql
-- Q25: بررسی رفع لاک
SELECT COUNT(*) FROM v$locked_object lo
JOIN dba_objects o ON lo.object_id = o.object_id
WHERE o.object_name = 'ACCOUNTMASTER';

-- اگر صفر شد → ادامه EOD از طریق UI (دکمه شروع مجدد)
```

<div dir="rtl">

#### ⚡ اقدام فوری (Quick Action Script)

</div>

```sql
-- Q26: اسکریپت تولید خودکار دستورات Kill برای تمام Blocker های ACCOUNTMASTER
-- ⚠️ خروجی را بررسی و سپس اجرا کنید
SELECT 'ALTER SYSTEM KILL SESSION ''' || s.sid || ',' || s.serial# || ''' IMMEDIATE; -- ' 
       || s.program || ' @ ' || s.machine
FROM v$session s
JOIN v$locked_object lo ON s.sid = lo.session_id
JOIN dba_objects o ON lo.object_id = o.object_id
WHERE o.object_name IN ('ACCOUNTMASTER', 'GENERALLEDGER', 'TRANSACTIONS', 'TERMLOANSDATA')
  AND lo.locked_mode >= 3
  AND s.username = 'DATAMATE'
  AND s.sid NOT IN (SELECT sid FROM dba_jobs_running);  -- جاب‌های EOD را Kill نکن!
```

<div dir="rtl">

---

### 6.2 Numeric Overflow

#### توضیح مشکل
یک مقدار محاسبه شده از ظرفیت متغیر PL/SQL یا ستون جدول بزرگتر است. مثلاً `NUMBER(21,6)` فقط تا ۱۵ رقم صحیح و ۶ رقم اعشار را پشتیبانی می‌کند.

#### خطاهای معمول

</div>

```
ORA-06502: PL/SQL: numeric or value error: number precision too large
ORA-01438: value larger than specified precision allowed for this column
```

<div dir="rtl">

#### مرحله ۱: شناسایی پروسیجر و متغیر

</div>

```sql
-- Q27: از DAYEND_PROCLOG_TABLE پیام خطا را بخوانید
SELECT PROCEDURENAME, ERRORMSG 
FROM DATAMATE.DAYEND_PROCLOG_TABLE 
WHERE ERRORCODE = -1
ORDER BY SEQ_ID DESC;
```

<div dir="rtl">

#### مرحله ۲: شناسایی داده‌های مشکل‌دار

</div>

```sql
-- Q28: بررسی مقادیر بزرگ در ACCOUNTMASTER (مرتبط با سود و مانده)
SELECT ACCOUNTNO, MODULE, SCHEME, BRANCH,
    INTERESTACCRUALPAYABLE,
    INTERESTBAL,
    DAYOPNLEDGERBAL,
    DAYOPNAVAILBAL,
    POSTPONEDINTEREST,
    LENGTH(TRIM(TO_CHAR(INTERESTACCRUALPAYABLE))) AS int_digits,
    LENGTH(TRIM(TO_CHAR(DAYOPNLEDGERBAL))) AS bal_digits
FROM DATAMATE.ACCOUNTMASTER
WHERE LENGTH(TRIM(TO_CHAR(NVL(INTERESTACCRUALPAYABLE,0)))) > 15
   OR LENGTH(TRIM(TO_CHAR(NVL(DAYOPNLEDGERBAL,0)))) > 15
   OR LENGTH(TRIM(TO_CHAR(NVL(INTERESTBAL,0)))) > 15;
```

```sql
-- Q29: بررسی مقادیر بزرگ در GENERALLEDGER
SELECT ACCOUNTISN, MODULE, SCHEME, BRANCH, OPENINGBALANCE,
    LENGTH(TRIM(TO_CHAR(NVL(OPENINGBALANCE,0)))) AS digits
FROM DATAMATE.GENERALLEDGER
WHERE LENGTH(TRIM(TO_CHAR(NVL(OPENINGBALANCE,0)))) > 21;
```

```sql
-- Q30: بررسی مقادیر بزرگ در TRANSACTIONS روز جاری
SELECT ACCOUNTISN, BRANCH, TXNNO, TXNAMOUNT, BALANCE, TXNINDICATOR,
    LENGTH(TRIM(TO_CHAR(NVL(TXNAMOUNT,0)))) AS amt_digits
FROM DATAMATE.TRANSACTIONS
WHERE ENTEREDDATE = (SELECT CURRENTDAY FROM DATAMATE.BRANCHPARAMETERS WHERE ISDATACENTRE = 'Y')
  AND LENGTH(TRIM(TO_CHAR(NVL(TXNAMOUNT,0)))) > 15
ORDER BY LENGTH(TRIM(TO_CHAR(NVL(TXNAMOUNT,0)))) DESC;
```

<div dir="rtl">

#### مرحله ۳: رفع

| وضعیت | اقدام |
|---|---|
| مقدار داده اشتباه است | اصلاح داده در جدول مربوطه |
| مقدار صحیح ولی ستون/متغیر کوچک است | ALTER TABLE برای افزایش سایز ستون |
| متغیر PL/SQL کوچک است | اصلاح تعریف متغیر در پروسیجر |

</div>

```sql
-- Q31: مثال - افزایش سایز ستون (در صورت نیاز)
-- ⚠️ ابتدا impact analysis انجام دهید
-- ALTER TABLE DATAMATE.GENERALLEDGER MODIFY OPENINGBALANCE NUMBER(27,6);

-- مثال - اصلاح داده غیرعادی (با احتیاط)
-- UPDATE DATAMATE.ACCOUNTMASTER 
-- SET INTERESTACCRUALPAYABLE = <مقدار_صحیح>
-- WHERE ACCOUNTNO = '<شماره_حساب>' AND BRANCH = '<شعبه>';
-- COMMIT;
```

<div dir="rtl">

---

### 6.3 Deadlock

#### توضیح مشکل
دو یا چند سشن EOD به‌صورت متقابل منتظر آزاد شدن لاک یکدیگر هستند. Oracle یکی از آنها را با خطای `ORA-00060` لغو می‌کند.

#### مرحله ۱: بررسی Alert Log

</div>

```sql
-- Q32: بررسی Deadlock در Alert Log (از طریق DBA)
-- مسیر Alert Log:
-- SELECT value FROM v$diag_info WHERE name = 'Diag Trace';
-- سپس: grep -i "deadlock" alert_<SID>.log | tail -20

-- Q33: بررسی Trace Files اخیر
SELECT 
    adr_home, originating_timestamp, message_text
FROM v$diag_alert_ext
WHERE message_text LIKE '%deadlock%'
  AND originating_timestamp > SYSDATE - 1
ORDER BY originating_timestamp DESC;
```

<div dir="rtl">

#### مرحله ۲: رفع
Deadlock معمولاً خودکار Rollback می‌شود. کافی است فرایند EOD را مجدداً Resume کنید.

اگر مکرراً رخ می‌دهد، بررسی کنید کدام پروسیجرها همزمان به یک جدول دسترسی دارند.

---

### 6.4 Timeout / Long Running

#### توضیح مشکل
یک پروسیجر بیش از حد معمول طول می‌کشد (مخصوصاً `DMSP_GLUPDATE_CORE` که طولانی‌ترین است).

#### مرحله ۱: شناسایی پروسیجر کند

</div>

```sql
-- Q34: مقایسه زمان اجرای فعلی با میانگین تاریخی
SELECT 
    j.PROCEDURENAME,
    TO_CHAR(j.START_TIME, 'HH24:MI:SS') start_time,
    ROUND((SYSDATE - j.START_TIME) * 24 * 60, 1) AS running_minutes,
    j.EXECUTIONFLAG,
    j.EXECUTIONFAILED
FROM DATAMATE.DAYEND_JOBLOG_TABLE j
WHERE j.END_TIME IS NULL  -- هنوز تمام نشده
  AND j.EXECUTIONFLAG = 'Y'
ORDER BY j.START_TIME;
```

```sql
-- Q35: بررسی اینکه سشن EOD واقعاً فعال است یا منتظر
SELECT 
    s.sid, s.serial#, s.status,
    s.event,
    s.seconds_in_wait,
    s.state,
    s.sql_id,
    (SELECT SUBSTR(sql_text,1,300) FROM v$sql WHERE sql_id = s.sql_id AND ROWNUM = 1) current_sql
FROM v$session s
JOIN dba_jobs_running r ON s.sid = r.sid
ORDER BY s.seconds_in_wait DESC;
```

<div dir="rtl">

#### مرحله ۲: علت‌یابی

| وضعیت | علت احتمالی | اقدام |
|---|---|---|
| `event = 'enq: TX - row lock contention'` | Row Lock | → بخش 6.1 |
| `event = 'db file sequential read'` | I/O بالا، Missing Index | بررسی Execution Plan |
| `event = 'direct path write temp'` | TEMP Tablespace | بررسی فضای TEMP |
| `event = 'log file sync'` | Commit کند | بررسی Redo Log |
| سشن ACTIVE ولی در حال پردازش | حجم داده بالا | صبر کنید |

</div>

```sql
-- Q36: بررسی Execution Plan پروسیجر کند
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR('&sql_id'));
```

<div dir="rtl">

---

### 6.5 Data Integrity / Business Logic Errors

#### خطاهای رایج کسب‌وکاری و رفع آنها

| پیام خطا | پروسیجر | علت | رفع |
|---|---|---|---|
| `DATACENTRE NOT SET` | DMSP_DAYEND_CORE | BRANCHPARAMETERS.ISDATACENTRE خالی | UPDATE BRANCHPARAMETERS SET ISDATACENTRE='Y' |
| `GLACCOUNTBALANCE NOT YET TRANSFER` | DMSP_DAYEND_CORE | رکورد قدیمی در GLACCOUNTBALANCETMP | بررسی Day Begin قبلی |
| `PRODUCTBALANCE NOT YET TRANSFER` | DMSP_DAYEND_CORE | رکورد قدیمی در PRODUCTBALANCETMP | بررسی Day Begin قبلی |
| `Day end already started` | DMSP_DAYEND_CORE | DAYENDEXEC خالی نشده | DELETE FROM DAYENDEXEC |
| `Difference GL Not Set In CURRENCYWISEGL` | DMSP_GLUPDATE_CORE | GL تفاوتی تعریف نشده | تنظیم CURRENCYWISEGL |
| `Trial Balance not tallied` | DMSP_GLUPDATE_CORE | مغایرت GL | → بخش 6.6 |

#### خطای تغییر طبقه تسهیلات

</div>

```sql
-- Q37: بررسی خطای تغییر طبقه (DMSP_MELAL_CHANGESTATUS_CORE)
-- ابتدا حساب مشکل‌دار را پیدا کنید
SELECT p.ERRORMSG, p.PROCEDURENAME
FROM DATAMATE.DAYEND_PROCLOG_TABLE p
WHERE p.PROCEDURENAME = 'DMSP_MELAL_CHANGESTATUS_CORE'
  AND p.ERRORCODE <> 0;

-- Q38: بررسی CLASSCODE فعلی حساب تسهیلاتی مشکل‌دار
SELECT A.ACCOUNTNO, A.BRANCH, A.MODULE, A.SCHEME,
       T.CLASSCODE, T.OVERDUEAMT, T.SUSPENDEDAMT, T.DOUBTFULAMT,
       A.INTERESTBAL, A.POSTPONEDINTEREST
FROM DATAMATE.ACCOUNTMASTER A
JOIN DATAMATE.TERMLOANSDATA T ON A.ACCOUNTNO = T.ACCOUNTNO AND A.BRANCH = T.BRANCH
WHERE A.ACCOUNTNO = '&account_no';

-- Q39: رفع - بازگرداندن CLASSCODE به مقدار روز قبل
-- ⚠️ با احتیاط اجرا شود
-- UPDATE DATAMATE.NPAHISTORY
-- SET CLASSCODE = (مقدار CLASSCODE روز قبل)
-- WHERE ACCOUNTNO = '&account_no'
--   AND PROCESSDATE = (SELECT CURRENTDAY FROM BRANCHPARAMETERS WHERE ISDATACENTRE = 'Y');
-- COMMIT;
```

<div dir="rtl">

---

### 6.6 GL Imbalance (عدم تراز Trial Balance)

#### توضیح
در `DMSP_GLUPDATE_CORE` مجموع Opening Balance تمام GL ها باید صفر باشد. اگر نباشد، مغایرت وجود دارد.

#### مرحله ۱: شناسایی مغایرت

</div>

```sql
-- Q40: بررسی تراز GL
SELECT 
    BRANCH,
    CURRENCYCODE,
    SUM(NVL(OPENINGBALANCE, 0)) AS total_opening_balance
FROM DATAMATE.GENERALLEDGER
GROUP BY BRANCH, CURRENCYCODE
HAVING SUM(NVL(OPENINGBALANCE, 0)) <> 0
ORDER BY ABS(SUM(NVL(OPENINGBALANCE, 0))) DESC;
```

<div dir="rtl">

#### مرحله ۲: پیدا کردن سند ناقص

</div>

```sql
-- Q41: پیدا کردن تراکنش‌های تک‌طرفه (فقط DR یا فقط CR)
SELECT 
    T.BRANCH, T.BATCHNO, T.ENTEREDDATE,
    SUM(CASE WHEN SUBSTR(TXNINDICATOR,3,2) = 'DR' THEN TXNAMOUNT ELSE 0 END) total_dr,
    SUM(CASE WHEN SUBSTR(TXNINDICATOR,3,2) = 'CR' THEN TXNAMOUNT ELSE 0 END) total_cr,
    SUM(CASE WHEN SUBSTR(TXNINDICATOR,3,2) = 'DR' THEN TXNAMOUNT ELSE 0 END) -
    SUM(CASE WHEN SUBSTR(TXNINDICATOR,3,2) = 'CR' THEN TXNAMOUNT ELSE 0 END) AS difference
FROM DATAMATE.TRANSACTIONS T
WHERE T.ENTEREDDATE = (SELECT CURRENTDAY FROM DATAMATE.BRANCHPARAMETERS WHERE ISDATACENTRE = 'Y')
GROUP BY T.BRANCH, T.BATCHNO, T.ENTEREDDATE
HAVING ABS(
    SUM(CASE WHEN SUBSTR(TXNINDICATOR,3,2) = 'DR' THEN TXNAMOUNT ELSE 0 END) -
    SUM(CASE WHEN SUBSTR(TXNINDICATOR,3,2) = 'CR' THEN TXNAMOUNT ELSE 0 END)
) > 0.01
ORDER BY ABS(
    SUM(CASE WHEN SUBSTR(TXNINDICATOR,3,2) = 'DR' THEN TXNAMOUNT ELSE 0 END) -
    SUM(CASE WHEN SUBSTR(TXNINDICATOR,3,2) = 'CR' THEN TXNAMOUNT ELSE 0 END)
) DESC;
```

```sql
-- Q42: جزئیات تراکنش ناتراز (BATCHNO از Q41)
SELECT 
    T.BRANCH, T.BATCHNO, T.TXNNO, T.ACCOUNTNO, T.MODULE, T.SCHEME,
    T.TXNINDICATOR, T.TXNAMOUNT, T.GLACCOUNTISN
FROM DATAMATE.TRANSACTIONS T
WHERE T.BATCHNO = &batch_no
  AND T.ENTEREDDATE = (SELECT CURRENTDAY FROM DATAMATE.BRANCHPARAMETERS WHERE ISDATACENTRE = 'Y')
ORDER BY T.TXNNO;

-- Q43: بررسی TRANSFERHEADER/TRANSFERDETAILS برای سند ناتراز
SELECT H.BATCHNO, H.BRANCH, D.ACCOUNTNO, D.TXNINDICATOR, D.TXNAMOUNT
FROM DATAMATE.TRANSFERHEADER H
JOIN DATAMATE.TRANSFERDETAILS D ON H.BATCHNO = D.BATCHNO AND H.BRANCH = D.BRANCH
WHERE H.BATCHNO = &batch_no
ORDER BY D.TXNNO;
```

<div dir="rtl">

#### مرحله ۳: رفع
تراکنش ناقص را با درج LEG مقابل (DR/CR) تکمیل کنید تا تراز برقرار شود. سپس EOD را Resume کنید.

---

### 6.7 Snapshot Too Old (ORA-01555)

#### توضیح
پروسیجرهای طولانی مانند `DMSP_GLUPDATE_CORE` ممکن است در حین خواندن داده‌ها با این خطا مواجه شوند.

#### رفع فوری

</div>

```sql
-- Q44: بررسی UNDO Retention
SHOW PARAMETER undo_retention;

-- اگر مقدار کم است (مثلاً زیر 3600):
-- ALTER SYSTEM SET UNDO_RETENTION = 7200 SCOPE=BOTH;

-- بررسی فضای UNDO
SELECT tablespace_name, 
       ROUND(SUM(bytes)/1024/1024) total_mb
FROM dba_data_files 
WHERE tablespace_name = (SELECT value FROM v$parameter WHERE name = 'undo_tablespace')
GROUP BY tablespace_name;
```

<div dir="rtl">

سپس EOD را Resume کنید.

---

### 6.8 Tablespace Full (ORA-01653/01654)

#### رفع فوری

</div>

```sql
-- Q45: شناسایی Tablespace پر شده
SELECT tablespace_name, 
       ROUND(SUM(bytes)/1024/1024) used_mb,
       ROUND(SUM(maxbytes)/1024/1024) max_mb
FROM dba_data_files
GROUP BY tablespace_name
ORDER BY SUM(bytes)/SUM(maxbytes) DESC;

-- اضافه کردن Datafile:
-- ALTER TABLESPACE <ts_name> ADD DATAFILE '<path>' SIZE 1G AUTOEXTEND ON MAXSIZE 10G;

-- یا فعال کردن AUTOEXTEND:
-- ALTER DATABASE DATAFILE '<file_path>' AUTOEXTEND ON MAXSIZE UNLIMITED;
```

<div dir="rtl">

---

## 7. روال ادامه (Resume) فرایند EOD

### 7.1 Resume از طریق UI (روش استاندارد)

**پیش‌نیازها:**
1. علت خطا شناسایی و رفع شده باشد
2. لاک‌ها آزاد شده باشند
3. DAYENDEXEC خالی شده باشد (سیستم خودکار حذف می‌کند)

**مراحل:**
1. بررسی `DAYENDLOG` → جاب‌هایی که `EXECUTIONFAILED='Y'` دارند مجدداً اجرا خواهند شد
2. جاب‌هایی که `EXECUTIONSTARTED='Y'` و `EXECUTIONFAILED='N'` دارند مجدداً اجرا **نخواهند** شد
3. دکمه شروع EOD را بزنید
4. سیستم از نقطه توقف ادامه می‌دهد

### 7.2 بررسی‌های قبل از Resume

</div>

```sql
-- Q46: وضعیت فعلی تمام جاب‌ها قبل از Resume
SELECT 
    PROCSEQ, PROCNAME, 
    EXECUTIONFLAG, EXECUTIONSTARTED, EXECUTIONFAILED,
    CASE 
        WHEN EXECUTIONFAILED = 'Y' THEN '→ این جاب مجدداً اجرا خواهد شد'
        WHEN EXECUTIONSTARTED = 'Y' THEN '→ تمام شده، اجرا نخواهد شد'
        WHEN EXECUTIONFLAG = 'Y' AND EXECUTIONSTARTED = 'N' THEN '→ در انتظار، اجرا خواهد شد'
        ELSE '→ شروع نشده، اجرا خواهد شد'
    END AS resume_action
FROM DATAMATE.DAYENDLOG
ORDER BY PROCSEQ;

-- Q47: بررسی DAYENDEXEC (باید خالی باشد برای Resume)
SELECT * FROM DATAMATE.DAYENDEXEC;
-- اگر خالی نیست:
-- DELETE FROM DATAMATE.DAYENDEXEC;
-- COMMIT;
```

<div dir="rtl">

### 7.3 ⚠️ هشدار مهم

> **هرگز** فلگ‌های `EXECUTIONSTARTED` یا `EXECUTIONFAILED` در جدول `DAYENDLOG` را به‌صورت دستی تغییر ندهید مگر اینکه کاملاً مطمئن باشید. تغییر نادرست این فلگ‌ها می‌تواند باعث شود جاب‌هایی که باید اجرا شوند اجرا نشوند یا جاب‌هایی که تمام شده‌اند دوباره اجرا شوند.

---

## 8. روال اجرای دستی مراحل EOD

### 8.1 چه زمانی نیاز به اجرای دستی است؟
- Resume خودکار کار نمی‌کند
- نیاز به اجرای انتخابی پروسیجرها
- مشکل در DBMS_JOB

### 8.2 ترتیب اجرای دستی پروسیجرهای فعال

> ⚠️ **هشدار:** اجرای دستی ریسک بالایی دارد. حتماً توالی وابستگی‌ها را رعایت کنید.

</div>

```sql
-- ========================================
-- اسکریپت اجرای دستی EOD (مرحله به مرحله)
-- ========================================
-- ⚠️ هر بلاک را جداگانه اجرا کنید و نتیجه را بررسی کنید
-- ⚠️ متغیرهای v_bank و v_date را تنظیم کنید

-- تنظیم متغیرها
VARIABLE v_result NUMBER;
VARIABLE v_message VARCHAR2(4000);

-- ======== مرحله 0: پارامترها ========
DEFINE v_bank = '075'   -- کد بانک خود را وارد کنید
DEFINE v_date = '09-MAY-2026'  -- تاریخ جاری را وارد کنید

-- ======== مرحله 1: JOB 3 - SWAPLOANANDCASA (مهم‌ترین) ========
-- این جاب شامل پروسیجرهای زیر است:

-- 1.1 DMSP_MARKDORMANTAPLYCHRGS_CORE (راکدی حساب)
BEGIN
    DMSP_MARKDORMANTAPLYCHRGS_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;
-- اگر v_result = 0 → ادامه، در غیر این صورت رفع خطا

-- 1.2 DMSP_APPLYSMSCHARGE (کارمزد پیامک)
BEGIN
    DMSP_APPLYSMSCHARGE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 1.3 DMSP_PULLTDINTTOLOAN_CORE (انتقال سود سپرده به تسهیلات)
BEGIN
    DMSP_PULLTDINTTOLOAN_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 1.4 DMSP_LOAN_SWAP_CORE (برداشت خودکار قسط)
BEGIN
    DMSP_LOAN_SWAP_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 1.5 CCSP_INTACCRUAL_CORE (سود کارت اعتباری)
BEGIN
    CCSP_INTACCRUAL_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 1.6 CCSP_CCTOBASESWAP_CORE
BEGIN
    CCSP_CCTOBASESWAP_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 1.7 CCSP_BASETOCCSWAP_CORE
BEGIN
    CCSP_BASETOCCSWAP_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 1.8 CCSP_COLLATERALRELEASE
BEGIN
    CCSP_COLLATERALRELEASE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 1.9 CCSP_YEARLYCHARGES
BEGIN
    CCSP_YEARLYCHARGES('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- ✅ JOB 3 COMPLETE → بروزرسانی DAYENDLOG
-- UPDATE DAYENDLOG SET EXECUTIONSTARTED='Y', EXECUTIONFLAG='Y' WHERE PROCSEQ=3;
-- COMMIT;


-- ======== مرحله 2: JOB 4 - DD (SB Interest) ========
-- وابسته به JOB 3
BEGIN
    DMSP_DAYENDSBINTACCRUAL_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), 'SYS', :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;


-- ======== مرحله 3: JOB 5 - TD ========
-- وابسته به JOB 3
BEGIN
    DMSP_TDINTACCRUAL_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;


-- ======== مرحله 4: JOB 6 - TL ========
-- وابسته به JOB 3

-- 4.1
BEGIN
    DMSP_TRFCOMMTOLOANAC_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 4.2
BEGIN
    DMSP_TLDAYEND_UPD_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 4.3
BEGIN
    DMSP_NPA_SCANNINGTL_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;


-- ======== مرحله 5: JOB 8,9,10 - TL Part 2 ========
-- وابسته به JOB 6

-- 5.1 سود معوق
BEGIN
    DMSP_UPDPOSTPONEDINTEREST_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 5.2 تغییر طبقه
BEGIN
    DMSP_MELAL_CHANGESTATUS_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 5.3 شناسایی سود تسهیلات
BEGIN
    DMSP_TL_INTACRRUAL_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;


-- ======== مرحله 6: JOB 11 - Credit Card ========
-- این جاب پروسیجرهای متعدد CC دارد - به ترتیب اجرا کنید
BEGIN
    CCSP_RECEIVABLE_INT_UPD_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
-- CCSP_EOD_CORE, CCSP_LOANACCOUNTOPEN_CORE, CCSP_MUSHRAKALOANACOPEN_CORE
-- CCSP_CHANGE_STATUS_CHAPP_CORE, CCSP_LOYALTYPOINTS_CORE
-- هر کدام را با الگوی مشابه اجرا کنید


-- ======== مرحله 7: JOB 12 - GL UPDATE (بحرانی‌ترین) ========
-- وابسته به همه جاب‌های قبلی

-- 7.1 واریز سود SB
BEGIN
    DMSP_INTERESTPOSTING_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 7.2 تسویه تراکنش‌های راه‌دور
BEGIN
    DMSP_INTERCHANGEGLNULLIFY_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 7.3 سود ارزی
BEGIN
    DMSP_INTACCRSBANDTDFRGN_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 7.4 تسویه کلر
BEGIN
    DMSP_AUTOPOSTTRANSACTION_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 7.5 تسعیر ارز
BEGIN
    DMSP_CURRENCYGAINLOSS_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 7.6 جریمه مشکوک‌الوصول
BEGIN
    DMSP_PENAL_BF_SUS_REV_REC('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- 7.7 ⭐ GLUPDATE (مهم‌ترین و طولانی‌ترین)
BEGIN
    DMSP_GLUPDATE_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;
-- ⏱️ این پروسیجر ممکن است ۳۰-۶۰ دقیقه طول بکشد


-- ======== مرحله 8: JOB 13 - UpdateAccountMaster ========
BEGIN
    DMSP_UPDATEACCOUNTMASTER_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;


-- ======== مرحله 9: JOB 15 - CommonProcForAll ========
BEGIN
    DMSP_COMMPROCFORALL_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;

-- DMSP_INITIALISE_CORE
BEGIN
    DMSP_INITIALISE_CORE('&v_bank', TO_DATE('&v_date','DD-MON-YYYY'), 'E', :v_result, :v_message);
END;
/
PRINT v_result;
PRINT v_message;


-- ======== مرحله 10: JOB 16 - پایان رسمی EOD ========
-- ⚠️ فقط پس از موفقیت تمام مراحل قبل
-- این جاب BRANCHPARAMETERS را بروزرسانی می‌کند
```

<div dir="rtl">

### 8.3 بروزرسانی دستی فلگ‌های DAYENDLOG (فقط در حالت اجرای دستی)

> ⚠️ فقط زمانی که پروسیجر را خودتان با موفقیت اجرا کرده‌اید

</div>

```sql
-- Q48: بروزرسانی وضعیت جاب پس از اجرای دستی موفق
UPDATE DATAMATE.DAYENDLOG 
SET EXECUTIONSTARTED = 'Y', EXECUTIONFLAG = 'Y', EXECUTIONFAILED = 'N'
WHERE PROCSEQ = &job_seq_number;
COMMIT;

-- Q49: ثبت لاگ دستی برای پروسیجر اجرا شده
INSERT INTO DATAMATE.DAYEND_PROCLOG_TABLE (SEQ_ID, START_TIME, END_TIME, ERRORCODE, ERRORMSG, PROCEDURENAME)
VALUES (DATAMATE.DAYEND_PROC_SEQ.NEXTVAL, &start_time, SYSDATE, 0, 'Manual execution successful', '&proc_name');
COMMIT;
```

<div dir="rtl">

---

## 9. چک‌لیست پس از اتمام EOD

### ✅ Post-EOD Validation Checklist

</div>

```sql
-- Q50: بررسی اتمام موفق تمام جاب‌ها
SELECT PROCSEQ, PROCNAME, EXECUTIONSTARTED, EXECUTIONFAILED,
    CASE WHEN EXECUTIONSTARTED = 'Y' AND EXECUTIONFAILED = 'N' THEN 'OK' ELSE 'PROBLEM!' END status
FROM DATAMATE.DAYENDLOG
ORDER BY PROCSEQ;

-- Q51: بررسی BRANCHPARAMETERS پس از EOD
SELECT BRANCH, CURRENTDAY, PREVIOUSDAY, 
    DAYENDCOMPLETED, DAYBEGINCOMPLETED, DAYENDSTARTED,
    READYFORDAYBEGIN, READYFORDAYEND
FROM DATAMATE.BRANCHPARAMETERS
WHERE ISDATACENTRE = 'Y';
-- مقادیر مورد انتظار: DAYENDCOMPLETED='Y', READYFORDAYBEGIN='Y', DAYENDSTARTED='N'

-- Q52: بررسی تعداد خطاها در PROCLOG
SELECT COUNT(*) AS error_count
FROM DATAMATE.DAYEND_PROCLOG_TABLE
WHERE ERRORCODE <> 0;

-- Q53: بررسی تراز GL پس از EOD
SELECT BRANCH, CURRENCYCODE, SUM(NVL(OPENINGBALANCE,0)) AS total_balance
FROM DATAMATE.GENERALLEDGER
GROUP BY BRANCH, CURRENCYCODE
HAVING SUM(NVL(OPENINGBALANCE,0)) <> 0;

-- Q54: بررسی زمان کل EOD
SELECT 
    MIN(START_TIME) AS eod_start,
    MAX(END_TIME) AS eod_end,
    ROUND((MAX(END_TIME) - MIN(START_TIME)) * 24 * 60, 1) AS total_minutes
FROM DATAMATE.DAYEND_PROCLOG_TABLE
WHERE ERRORCODE = 0;

-- Q55: بررسی DAYENDEXEC (باید خالی باشد)
SELECT COUNT(*) FROM DATAMATE.DAYENDEXEC;

-- Q56: بررسی درج رکوردها در GLACCOUNTBALANCETMP
SELECT COUNT(*) AS records_count, GLDATE
FROM DATAMATE.GLACCOUNTBALANCETMP
GROUP BY GLDATE
ORDER BY GLDATE DESC;
```

<div dir="rtl">

---

## 10. کوئری‌های تشخیصی مرجع (Quick Reference)

### 10.1 کوئری‌های Lock Detection

</div>

```sql
-- QR01: لاک‌های فعال روی ACCOUNTMASTER (سریع‌ترین راه تشخیص)
SELECT s.sid, s.serial#, s.program, s.machine, s.last_call_et wait_sec,
       DECODE(lo.locked_mode, 2,'ROW-S', 3,'ROW-X', 4,'SHARE', 5,'S/ROW-X', 6,'EXCLUSIVE') lock_mode
FROM v$locked_object lo
JOIN dba_objects o ON lo.object_id = o.object_id
JOIN v$session s ON lo.session_id = s.sid
WHERE o.object_name = 'ACCOUNTMASTER' AND lo.locked_mode >= 3;

-- QR02: Blocking Tree (درخت انسداد)
SELECT LPAD(' ', 2*(LEVEL-1)) || sid || ' (' || NVL(username,'?') || '/' || NVL(program,'?') || ')' info,
       blocking_session, event, seconds_in_wait
FROM v$session
WHERE blocking_session IS NOT NULL OR sid IN (SELECT blocking_session FROM v$session WHERE blocking_session IS NOT NULL)
START WITH blocking_session IS NULL AND sid IN (SELECT blocking_session FROM v$session WHERE blocking_session IS NOT NULL)
CONNECT BY PRIOR sid = blocking_session;

-- QR03: Enqueue Waits (صف‌های انتظار)
SELECT 
    s.sid, s.serial#, s.username, s.program,
    w.event, w.p1text, w.p2text, w.p3text,
    w.seconds_in_wait, w.state
FROM v$session_wait w
JOIN v$session s ON w.sid = s.sid
WHERE w.event LIKE 'enq:%'
ORDER BY w.seconds_in_wait DESC;
```

<div dir="rtl">

### 10.2 کوئری‌های Session Analysis

</div>

```sql
-- QR04: تمام سشن‌های DATAMATE و وضعیت آنها
SELECT sid, serial#, status, program, machine, 
       TO_CHAR(logon_time, 'HH24:MI:SS') logon,
       last_call_et wait_sec, event, sql_id
FROM v$session WHERE username = 'DATAMATE' AND type = 'USER'
ORDER BY status, last_call_et DESC;

-- QR05: سشن‌هایی که بیش از 5 دقیقه منتظرند
SELECT sid, serial#, program, event, seconds_in_wait,
       (SELECT SUBSTR(sql_text,1,200) FROM v$sql WHERE sql_id = s.sql_id AND ROWNUM = 1) sql_text
FROM v$session s
WHERE username = 'DATAMATE' AND seconds_in_wait > 300
ORDER BY seconds_in_wait DESC;

-- QR06: DBMS_JOB های در حال اجرا (مرتبط با EOD)
SELECT j.job, j.what, r.sid, s.status, s.event, s.seconds_in_wait
FROM dba_jobs_running r
JOIN dba_jobs j ON r.job = j.job
JOIN v$session s ON r.sid = s.sid
ORDER BY j.job;
```

<div dir="rtl">

### 10.3 کوئری‌های تاریخچه و آنالیز

</div>

```sql
-- QR07: تاریخچه زمان اجرای هر پروسیجر (برای شناسایی پروسیجرهای کند)
SELECT 
    PROCEDURENAME,
    TO_CHAR(START_TIME, 'YYYY/MM/DD') run_date,
    ROUND((END_TIME - START_TIME) * 24 * 60, 1) AS duration_min
FROM DATAMATE.DAYEND_PROCLOG_TABLE_HIST
WHERE ERRORCODE = 0
ORDER BY PROCEDURENAME, START_TIME DESC;

-- QR08: آنالیز پروسیجرهای خطادار تاریخی
SELECT 
    PROCEDURENAME,
    COUNT(*) AS error_count,
    MAX(ERRORMSG) AS last_error
FROM DATAMATE.DAYEND_PROCLOG_TABLE_HIST
WHERE ERRORCODE <> 0
GROUP BY PROCEDURENAME
ORDER BY error_count DESC;
```

<div dir="rtl">

---

## 11. پیشنهادات بهبود (بدون تغییر ساختار)

### 11.1 اقدامات پیشگیرانه

| اقدام | توضیح | اولویت |
|---|---|---|
| **Pre-EOD Lock Check Automation** | ایجاد یک اسکریپت که ۵ دقیقه قبل از ساعت 00:10 لاک‌های جداول حساس را بررسی و گزارش/alert ارسال کند | بالا |
| **Kill Session Script** | آماده‌سازی اسکریپت Kill Session برای برنامه‌های غیر EOD قبل از شروع، با لیست سفید برنامه‌ها | بالا |
| **Stop External Services** | متوقف کردن سرویس‌های غیرضروری (مانند سرویس‌های آنلاین) ۵ دقیقه قبل از شروع EOD | بالا |
| **UNDO Retention** | تنظیم `UNDO_RETENTION` به حداقل ۷۲۰۰ ثانیه (۲ ساعت) | متوسط |
| **Tablespace Monitoring** | بررسی خودکار فضای Tablespace ها هر ساعت و alert در صورت پر شدن ۸۵٪ | متوسط |
| **Statistics Update** | جمع‌آوری آمار جداول بحرانی (`DBMS_STATS`) هفتگی برای بهبود Execution Plan | متوسط |

### 11.2 اسکریپت پیشنهادی Pre-EOD Auto-Check

</div>

```sql
-- اسکریپت Pre-EOD: قابل زمان‌بندی با DBMS_SCHEDULER در ساعت 00:05
CREATE OR REPLACE PROCEDURE DATAMATE.SP_PRE_EOD_CHECK AS
    v_lock_count NUMBER;
    v_dayendexec_count NUMBER;
    v_stale_gl NUMBER;
    v_stale_prod NUMBER;
    v_issues VARCHAR2(4000) := '';
BEGIN
    -- بررسی لاک‌ها
    SELECT COUNT(*) INTO v_lock_count
    FROM v$locked_object lo
    JOIN dba_objects o ON lo.object_id = o.object_id
    WHERE o.object_name IN ('ACCOUNTMASTER','GENERALLEDGER','TRANSACTIONS','TERMLOANSDATA')
      AND lo.locked_mode >= 3;
    
    IF v_lock_count > 0 THEN
        v_issues := v_issues || 'WARNING: ' || v_lock_count || ' active locks on critical tables. ';
    END IF;
    
    -- بررسی DAYENDEXEC
    SELECT COUNT(*) INTO v_dayendexec_count FROM DAYENDEXEC;
    IF v_dayendexec_count > 0 THEN
        v_issues := v_issues || 'ERROR: DAYENDEXEC not empty - previous EOD incomplete. ';
    END IF;
    
    -- بررسی داده‌های منقضی
    SELECT COUNT(*) INTO v_stale_gl FROM GLACCOUNTBALANCETMP 
    WHERE GLDATE < (SELECT CURRENTDAY FROM BRANCHPARAMETERS WHERE ISDATACENTRE = 'Y');
    IF v_stale_gl > 0 THEN
        v_issues := v_issues || 'ERROR: Stale GLACCOUNTBALANCETMP records found. ';
    END IF;
    
    SELECT COUNT(*) INTO v_stale_prod FROM PRODUCTBALANCETMP 
    WHERE PRODUCTDATE < (SELECT CURRENTDAY FROM BRANCHPARAMETERS WHERE ISDATACENTRE = 'Y');
    IF v_stale_prod > 0 THEN
        v_issues := v_issues || 'ERROR: Stale PRODUCTBALANCETMP records found. ';
    END IF;
    
    -- ثبت نتیجه
    IF v_issues IS NOT NULL THEN
        -- می‌توانید Alert ایمیل یا SMS ارسال کنید
        INSERT INTO DATAMATE.PRE_EOD_CHECK_LOG (CHECK_TIME, STATUS, DETAILS)
        VALUES (SYSDATE, 'FAILED', v_issues);
    ELSE
        INSERT INTO DATAMATE.PRE_EOD_CHECK_LOG (CHECK_TIME, STATUS, DETAILS)
        VALUES (SYSDATE, 'PASSED', 'All pre-EOD checks passed.');
    END IF;
    COMMIT;
END;
/
```

<div dir="rtl">

### 11.3 ماتریس ارتباط سریع (Escalation Matrix)

| سطح | زمان مجاز | مسئول | اقدام |
|---|---|---|---|
| **سطح ۱** | ۰-۱۵ دقیقه | اپراتور شب | اجرای کوئری‌های Q20-Q21 و شناسایی خطا |
| **سطح ۲** | ۱۵-۳۰ دقیقه | DBA ارشد | بررسی لاک‌ها، Kill Session، Resume |
| **سطح ۳** | ۳۰-۶۰ دقیقه | تیم توسعه | بررسی خطای کسب‌وکاری، اصلاح داده |
| **سطح ۴** | ۶۰+ دقیقه | مدیر فنی | تصمیم‌گیری برای اجرای دستی |

### 11.4 قالب گزارش حادثه (Incident Report Template)

</div>

```
┌─────────────────────────────────────────────────┐
│  گزارش حادثه فرایند پایان روز                    │
├─────────────────────────────────────────────────┤
│ تاریخ:                                           │
│ ساعت شروع EOD:                                  │
│ ساعت وقوع خطا:                                  │
│ ساعت رفع خطا:                                   │
│ ساعت پایان EOD:                                  │
│ مدت توقف (دقیقه):                                │
├─────────────────────────────────────────────────┤
│ جاب خطادار:                                      │
│ پروسیجر خطادار:                                  │
│ نوع خطا: □ Lock  □ Overflow  □ Logic  □ سایر    │
│ پیام خطا:                                        │
├─────────────────────────────────────────────────┤
│ علت ریشه‌ای:                                     │
│ اقدامات انجام شده:                               │
│ روش Resume: □ خودکار (UI)  □ دستی               │
├─────────────────────────────────────────────────┤
│ اقدامات پیشگیرانه پیشنهادی:                     │
│                                                  │
│ امضای مسئول:                                     │
└─────────────────────────────────────────────────┘
```

<div dir="rtl">

---

## پیوست: نقشه وابستگی جاب‌ها (Dependency Map)

</div>

```
                    ┌──────────┐
              ┌─────┤  JOB 3   ├─────┐
              │     │ SWAP/CASA│     │
              │     └────┬─────┘     │
              │          │           │
        ┌─────▼───┐ ┌───▼────┐ ┌───▼────┐
        │  JOB 4  │ │ JOB 5  │ │ JOB 6  │
        │ DD(SB)  │ │ TD     │ │ TL     │
        └─────────┘ └────────┘ └──┬─────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
              ┌─────▼───┐  ┌─────▼────┐  ┌─────▼────┐
              │  JOB 8  │  │  JOB 9   │  │  JOB 10  │
              │ PostpInt│  │ ChgStatus│  │ TL Accrl │
              └─────────┘  └──────────┘  └────┬─────┘
                                               │
                                         ┌─────▼────┐
                                         │  JOB 11  │
                                         │  CC EOD  │
                                         └────┬─────┘
                                               │
        ═══════════════════════════════════════╪═══ (ALL jobs must complete)
                                               │
                                         ┌─────▼────┐
                                         │  JOB 12  │ ⭐
                                         │  GL UPD  │
                                         └────┬─────┘
                                               │
                                         ┌─────▼────┐
                                         │  JOB 13  │
                                         │ AcctMstr │
                                         └────┬─────┘
                                               │
                                         ┌─────▼────┐
                                         │  JOB 15  │
                                         │ CommProc │
                                         └────┬─────┘
                                               │
                                         ┌─────▼────┐
                                         │  JOB 16  │
                                         │  FINISH  │
                                         └──────────┘
```

<div dir="rtl">

---

> **یادآوری نهایی:**  
> این مستند یک مرجع زنده (Living Document) است. پس از هر حادثه EOD، لطفاً سناریوی جدید و راه‌حل آن را به بخش ۶ اضافه کنید تا دانش تیم به‌صورت تجمعی افزایش یابد.

</div>

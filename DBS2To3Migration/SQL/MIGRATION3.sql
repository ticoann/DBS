--run the alter command in sqlplus.
alter session set NLS_DATE_FORMAT='yyyy/mm/dd:hh:mi:ssam';

spool mig-3.log;
select sysdate from dual;

ALTER TABLE FILE_LUMIS DROP PRIMARY KEY;
ALTER TABLE FILE_LUMIS DROP constraint TUC_FLM_1;
ALTER TABLE FILE_LUMIS DROP constraint FL_FLM;
DROP index IDX_FLM_1;

INSERT /*+ append */ INTO FILE_LUMIS(FILE_LUMI_ID, RUN_NUM, LUMI_SECTION_NUM, FILE_ID)
SELECT FRL.ID, FRL.RUN, FRL.LUMI, FRL.FILEID FROM CMS_DBS_PROD_GLOBAL.FILERUNLUMI FRL;
commit;
select 'Done insert FILE_LUMIS' from dual;
select sysdate from dual;

ALTER TABLE FILE_LUMIS ADD (
  CONSTRAINT FL_FLM
 FOREIGN KEY (FILE_ID)
 REFERENCES FILES (FILE_ID)
    ON DELETE CASCADE);

CREATE INDEX IDX_FLM_1 ON FILE_LUMIS
(FILE_ID);

--Seperate into two steps to save temp segment table sapce
ALTER TABLE FILE_LUMIS ADD (
  CONSTRAINT PK_FLM
 PRIMARY KEY
 (FILE_LUMI_ID)
    USING INDEX);

ALTER TABLE FILE_LUMIS ADD ( 
  CONSTRAINT TUC_FLM_1
 UNIQUE (RUN_NUM, LUMI_SECTION_NUM, FILE_ID)
    USING INDEX
    );
select 'Done recreate  FILE_LUMIS constraint' from dual;
select sysdate from dual;

spool off;

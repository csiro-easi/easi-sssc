PRAGMA foreign_keys=OFF;
begin transaction;

CREATE TABLE "applicationsignature" ("id" INTEGER NOT NULL PRIMARY KEY, "application_id" INTEGER NOT NULL, "signature_id" INTEGER NOT NULL, FOREIGN KEY ("application_id") REFERENCES "application" ("id"), FOREIGN KEY ("signature_id") REFERENCES "signature" ("id") ON DELETE CASCADE);
CREATE INDEX "applicationsignature_application_id" ON "applicationsignature" ("application_id");
CREATE UNIQUE INDEX "applicationsignature_signature_id" ON "applicationsignature" ("signature_id");

PRAGMA foreign_key_check;
commit;
PRAGMA foreign_keys;

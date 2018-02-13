PRAGMA foreign_keys=OFF;
begin transaction;


CREATE TABLE "application" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "description" TEXT NOT NULL, "created_at" DATETIME NOT NULL, "version" INTEGER NOT NULL, "entry_hash" VARCHAR(255), "published" INTEGER NOT NULL, "icon" VARCHAR(255), "url_template" VARCHAR(255), "latest_id" INTEGER, FOREIGN KEY ("latest_id") REFERENCES "application" ("id"));
CREATE INDEX "application_latest_id" ON "application" ("latest_id");

CREATE TABLE "applicationsolution" ("id" INTEGER NOT NULL PRIMARY KEY, "app_id" INTEGER NOT NULL, "solution_id" INTEGER NOT NULL, FOREIGN KEY ("app_id") REFERENCES "application" ("id"), FOREIGN KEY ("solution_id") REFERENCES "solution" ("id"));
CREATE INDEX "applicationsolution_app_id" ON "applicationsolution" ("app_id");
CREATE INDEX "applicationsolution_solution_id" ON "applicationsolution" ("solution_id");


PRAGMA foreign_key_check;
commit;
PRAGMA foreign_keys;

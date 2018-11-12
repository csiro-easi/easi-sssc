PRAGMA foreign_keys=OFF;
begin transaction;

CREATE TABLE "new_application" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "description" TEXT NOT NULL, "created_at" DATETIME NOT NULL, "version" INTEGER NOT NULL, "entry_hash" VARCHAR(255), "published" INTEGER NOT NULL, "icon" VARCHAR(255), "author_id" INTEGER NOT NULL, "url_template" VARCHAR(255), "latest_id" INTEGER, FOREIGN KEY ("author_id") REFERENCES "user" ("id"), FOREIGN KEY ("latest_id") REFERENCES "application" ("id"));

insert into "new_application" select "id", "name", "description", "created_at", "version", "entry_hash", "published", "icon", 1 as "author_id", "url_template", "latest_id" from "application";

drop table "application";

alter table "new_application" rename to "application";

CREATE INDEX "application_author_id" ON "application" ("author_id");
CREATE INDEX "application_latest_id" ON "application" ("latest_id");

PRAGMA foreign_key_check;
commit;
PRAGMA foreign_keys;

PRAGMA foreign_keys=OFF;
begin transaction;


CREATE TABLE "new_problem" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "description" TEXT NOT NULL, "created_at" DATETIME NOT NULL, "version" INTEGER NOT NULL, "entry_hash" VARCHAR(255), "published" INTEGER NOT NULL, "author_id" INTEGER NOT NULL, "latest_id" INTEGER, FOREIGN KEY ("author_id") REFERENCES "user" ("id"), FOREIGN KEY ("latest_id") REFERENCES "problem" ("id"));

insert into "new_problem" select "id", "name", "description", "created_at", "version", "entry_hash", "author_id", "latest_id", 1 as "published" from "problem";

drop table "problem";

alter table "new_problem" rename to "problem";

CREATE INDEX "problem_author_id" ON "problem" ("author_id");
CREATE INDEX "problem_latest_id" ON "problem" ("latest_id");


CREATE TABLE "new_toolbox" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "description" TEXT NOT NULL, "created_at" DATETIME NOT NULL, "version" INTEGER NOT NULL, "entry_hash" VARCHAR(255), "published" INTEGER NOT NULL, "author_id" INTEGER NOT NULL, "latest_id" INTEGER, "homepage" VARCHAR(255), "license_id" INTEGER NOT NULL, "source_id" INTEGER, "command" VARCHAR(255), "puppet" VARCHAR(255), "puppet_hash" VARCHAR(255) NOT NULL, FOREIGN KEY ("author_id") REFERENCES "user" ("id"), FOREIGN KEY ("latest_id") REFERENCES "toolbox" ("id"), FOREIGN KEY ("license_id") REFERENCES "license" ("id"), FOREIGN KEY ("source_id") REFERENCES "source" ("id"));

insert into "new_toolbox" select id, name, description, created_at, version, entry_hash, 1 as published, author_id, latest_id, homepage, license_id, source_id, command, puppet, puppet_hash from "toolbox";

drop table "toolbox";

alter table "new_toolbox" rename to "toolbox";

CREATE INDEX "toolbox_author_id" ON "toolbox" ("author_id");
CREATE INDEX "toolbox_latest_id" ON "toolbox" ("latest_id");
CREATE INDEX "toolbox_license_id" ON "toolbox" ("license_id");
CREATE INDEX "toolbox_source_id" ON "toolbox" ("source_id");


CREATE TABLE "new_solution" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "description" TEXT NOT NULL, "created_at" DATETIME NOT NULL, "version" INTEGER NOT NULL, "entry_hash" VARCHAR(255), "published" INTEGER NOT NULL, "author_id" INTEGER NOT NULL, "latest_id" INTEGER, "problem_id" INTEGER NOT NULL, "runtime" VARCHAR(255) NOT NULL, "template" VARCHAR(255) NOT NULL, "template_hash" VARCHAR(255) NOT NULL, FOREIGN KEY ("author_id") REFERENCES "user" ("id"), FOREIGN KEY ("latest_id") REFERENCES "solution" ("id"), FOREIGN KEY ("problem_id") REFERENCES "problem" ("id"));

insert into "new_solution" select id, name, description, created_at, version, entry_hash, 1 as published, author_id, latest_id, problem_id, runtime, template, template_hash from "solution";

drop table "solution";
alter table "new_solution" rename to "solution";

CREATE INDEX "solution_author_id" ON "solution" ("author_id");
CREATE INDEX "solution_latest_id" ON "solution" ("latest_id");
CREATE INDEX "solution_problem_id" ON "solution" ("problem_id");


PRAGMA foreign_key_check;
commit;
PRAGMA foreign_keys;

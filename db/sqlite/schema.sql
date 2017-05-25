CREATE TABLE "problemdigest" ("id" INTEGER NOT NULL PRIMARY KEY, "digest" BLOB NOT NULL, "created_at" DATETIME NOT NULL, "user_id_id" INTEGER, "user_key" VARCHAR(255), "entry_id_id" INTEGER NOT NULL, FOREIGN KEY ("user_id_id") REFERENCES "user" ("id"), FOREIGN KEY ("entry_id_id") REFERENCES "problem" ("id"));
CREATE INDEX "problemdigest_user_id_id" ON "problemdigest" ("user_id_id");
CREATE INDEX "problemdigest_entry_id_id" ON "problemdigest" ("entry_id_id");
CREATE TABLE "solutiondigest" ("id" INTEGER NOT NULL PRIMARY KEY, "digest" BLOB NOT NULL, "created_at" DATETIME NOT NULL, "user_id_id" INTEGER, "user_key" VARCHAR(255), "entry_id_id" INTEGER NOT NULL, FOREIGN KEY ("user_id_id") REFERENCES "user" ("id"), FOREIGN KEY ("entry_id_id") REFERENCES "solution" ("id"));
CREATE INDEX "solutiondigest_user_id_id" ON "solutiondigest" ("user_id_id");
CREATE INDEX "solutiondigest_entry_id_id" ON "solutiondigest" ("entry_id_id");
CREATE TABLE "toolboxdigest" ("id" INTEGER NOT NULL PRIMARY KEY, "digest" BLOB NOT NULL, "created_at" DATETIME NOT NULL, "user_id_id" INTEGER, "user_key" VARCHAR(255), "entry_id_id" INTEGER NOT NULL, FOREIGN KEY ("user_id_id") REFERENCES "user" ("id"), FOREIGN KEY ("entry_id_id") REFERENCES "toolbox" ("id"));
CREATE INDEX "toolboxdigest_user_id_id" ON "toolboxdigest" ("user_id_id");
CREATE INDEX "toolboxdigest_entry_id_id" ON "toolboxdigest" ("entry_id_id");
CREATE TABLE "resource" ("id" INTEGER NOT NULL PRIMARY KEY, "url" VARCHAR(255) NOT NULL, "retrieved_at" DATETIME, "digest" BLOB);
CREATE TABLE "solutiontemplate" ("id" INTEGER NOT NULL PRIMARY KEY, "solution_id" INTEGER NOT NULL, "template_id" INTEGER NOT NULL, FOREIGN KEY ("solution_id") REFERENCES "solution" ("id"), FOREIGN KEY ("template_id") REFERENCES "resource" ("id"));
CREATE UNIQUE INDEX "solutiontemplate_solution_id" ON "solutiontemplate" ("solution_id");
CREATE UNIQUE INDEX "solutiontemplate_template_id" ON "solutiontemplate" ("template_id");
CREATE TABLE "toolboxpuppet" ("id" INTEGER NOT NULL PRIMARY KEY, "toolbox_id" INTEGER NOT NULL, "puppet_id" INTEGER NOT NULL, FOREIGN KEY ("toolbox_id") REFERENCES "toolbox" ("id"), FOREIGN KEY ("puppet_id") REFERENCES "resource" ("id"));
CREATE INDEX "toolboxpuppet_toolbox_id" ON "toolboxpuppet" ("toolbox_id");
CREATE INDEX "toolboxpuppet_puppet_id" ON "toolboxpuppet" ("puppet_id");
CREATE TABLE "license" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "url" VARCHAR(255), "text" TEXT);
CREATE UNIQUE INDEX "license_name" ON "license" ("name");
CREATE TABLE "role" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "description" TEXT);
CREATE UNIQUE INDEX "role_name" ON "role" ("name");
CREATE TABLE "source" ("id" INTEGER NOT NULL PRIMARY KEY, "type" VARCHAR(255) NOT NULL, "url" VARCHAR(255) NOT NULL, "checkout" VARCHAR(255), "setup" TEXT);
CREATE TABLE "user" ("id" INTEGER NOT NULL PRIMARY KEY, "email" VARCHAR(255) NOT NULL, "password" TEXT NOT NULL, "name" VARCHAR(255) NOT NULL, "active" INTEGER NOT NULL, "confirmed_at" DATETIME);
CREATE UNIQUE INDEX "user_email" ON "user" ("email");
CREATE TABLE "problem" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "description" TEXT NOT NULL, "created_at" DATETIME NOT NULL, "version" INTEGER NOT NULL, "entry_hash" VARCHAR(255), "published" INTEGER NOT NULL, "author_id" INTEGER NOT NULL, "latest_id" INTEGER, FOREIGN KEY ("author_id") REFERENCES "user" ("id"), FOREIGN KEY ("latest_id") REFERENCES "problem" ("id"));
CREATE INDEX "problem_author_id" ON "problem" ("author_id");
CREATE INDEX "problem_latest_id" ON "problem" ("latest_id");
CREATE TABLE "problemtag" ("id" INTEGER NOT NULL PRIMARY KEY, "tag" VARCHAR(255) NOT NULL, "entry_id" INTEGER NOT NULL, FOREIGN KEY ("entry_id") REFERENCES "problem" ("id"));
CREATE INDEX "problemtag_entry_id" ON "problemtag" ("entry_id");
CREATE TABLE "solution" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "description" TEXT NOT NULL, "created_at" DATETIME NOT NULL, "version" INTEGER NOT NULL, "entry_hash" VARCHAR(255), "published" INTEGER NOT NULL, "author_id" INTEGER NOT NULL, "latest_id" INTEGER, "problem_id" INTEGER NOT NULL, "runtime" VARCHAR(255) NOT NULL, "template" VARCHAR(255) NOT NULL, "template_hash" VARCHAR(255) NOT NULL, FOREIGN KEY ("author_id") REFERENCES "user" ("id"), FOREIGN KEY ("latest_id") REFERENCES "solution" ("id"), FOREIGN KEY ("problem_id") REFERENCES "problem" ("id"));
CREATE INDEX "solution_author_id" ON "solution" ("author_id");
CREATE INDEX "solution_latest_id" ON "solution" ("latest_id");
CREATE INDEX "solution_problem_id" ON "solution" ("problem_id");
CREATE TABLE "solutionimage" ("id" INTEGER NOT NULL PRIMARY KEY, "provider" VARCHAR(255) NOT NULL, "image_id" VARCHAR(255) NOT NULL, "solution_id" INTEGER NOT NULL, FOREIGN KEY ("solution_id") REFERENCES "solution" ("id"));
CREATE INDEX "solutionimage_solution_id" ON "solutionimage" ("solution_id");
CREATE TABLE "solutiontag" ("id" INTEGER NOT NULL PRIMARY KEY, "tag" VARCHAR(255) NOT NULL, "entry_id" INTEGER NOT NULL, FOREIGN KEY ("entry_id") REFERENCES "solution" ("id"));
CREATE INDEX "solutiontag_entry_id" ON "solutiontag" ("entry_id");
CREATE TABLE "solutionvar" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "type" VARCHAR(255) NOT NULL, "label" VARCHAR(255), "description" TEXT, "optional" INTEGER NOT NULL, "default" VARCHAR(255), "min" REAL, "max" REAL, "step" REAL, "values" VARCHAR(255), "solution_id" INTEGER NOT NULL, FOREIGN KEY ("solution_id") REFERENCES "solution" ("id"));
CREATE INDEX "solutionvar_solution_id" ON "solutionvar" ("solution_id");
CREATE TABLE "solutiondependency" ("id" INTEGER NOT NULL PRIMARY KEY, "type" VARCHAR(255) NOT NULL, "identifier" VARCHAR(255) NOT NULL, "version" VARCHAR(255), "repository" VARCHAR(255), "solution_id" INTEGER NOT NULL, FOREIGN KEY ("solution_id") REFERENCES "solution" ("id"));
CREATE INDEX "solutiondependency_solution_id" ON "solutiondependency" ("solution_id");
CREATE TABLE "publickey" ("id" INTEGER NOT NULL PRIMARY KEY, "user_id" INTEGER NOT NULL, "registered_at" DATETIME NOT NULL, "key" TEXT NOT NULL, FOREIGN KEY ("user_id") REFERENCES "user" ("id"));
CREATE INDEX "publickey_user_id" ON "publickey" ("user_id");
CREATE TABLE "signature" ("id" INTEGER NOT NULL PRIMARY KEY, "signature" VARCHAR(255) NOT NULL, "signed_string" TEXT NOT NULL, "created_at" DATETIME NOT NULL, "user_id_id" INTEGER, "public_key_id" INTEGER NOT NULL, FOREIGN KEY ("user_id_id") REFERENCES "user" ("id"), FOREIGN KEY ("public_key_id") REFERENCES "publickey" ("id"));
CREATE INDEX "signature_user_id_id" ON "signature" ("user_id_id");
CREATE INDEX "signature_public_key_id" ON "signature" ("public_key_id");
CREATE TABLE "problemsignature" ("id" INTEGER NOT NULL PRIMARY KEY, "problem_id" INTEGER NOT NULL, "signature_id" INTEGER NOT NULL, FOREIGN KEY ("problem_id") REFERENCES "problem" ("id"), FOREIGN KEY ("signature_id") REFERENCES "signature" ("id") ON DELETE CASCADE);
CREATE INDEX "problemsignature_problem_id" ON "problemsignature" ("problem_id");
CREATE UNIQUE INDEX "problemsignature_signature_id" ON "problemsignature" ("signature_id");
CREATE TABLE "solutionsignature" ("id" INTEGER NOT NULL PRIMARY KEY, "solution_id" INTEGER NOT NULL, "signature_id" INTEGER NOT NULL, FOREIGN KEY ("solution_id") REFERENCES "solution" ("id"), FOREIGN KEY ("signature_id") REFERENCES "signature" ("id") ON DELETE CASCADE);
CREATE INDEX "solutionsignature_solution_id" ON "solutionsignature" ("solution_id");
CREATE UNIQUE INDEX "solutionsignature_signature_id" ON "solutionsignature" ("signature_id");
CREATE TABLE "toolbox" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "description" TEXT NOT NULL, "created_at" DATETIME NOT NULL, "version" INTEGER NOT NULL, "entry_hash" VARCHAR(255), "published" INTEGER NOT NULL, "author_id" INTEGER NOT NULL, "latest_id" INTEGER, "homepage" VARCHAR(255), "license_id" INTEGER NOT NULL, "source_id" INTEGER, "command" VARCHAR(255), "puppet" VARCHAR(255), "puppet_hash" VARCHAR(255) NOT NULL, FOREIGN KEY ("author_id") REFERENCES "user" ("id"), FOREIGN KEY ("latest_id") REFERENCES "toolbox" ("id"), FOREIGN KEY ("license_id") REFERENCES "license" ("id"), FOREIGN KEY ("source_id") REFERENCES "source" ("id"));
CREATE INDEX "toolbox_author_id" ON "toolbox" ("author_id");
CREATE INDEX "toolbox_latest_id" ON "toolbox" ("latest_id");
CREATE INDEX "toolbox_license_id" ON "toolbox" ("license_id");
CREATE INDEX "toolbox_source_id" ON "toolbox" ("source_id");
CREATE TABLE "toolboximage" ("id" INTEGER NOT NULL PRIMARY KEY, "provider" VARCHAR(255) NOT NULL, "image_id" VARCHAR(255) NOT NULL, "toolbox_id" INTEGER NOT NULL, FOREIGN KEY ("toolbox_id") REFERENCES "toolbox" ("id"));
CREATE INDEX "toolboximage_toolbox_id" ON "toolboximage" ("toolbox_id");
CREATE TABLE "toolboxtag" ("id" INTEGER NOT NULL PRIMARY KEY, "tag" VARCHAR(255) NOT NULL, "entry_id" INTEGER NOT NULL, FOREIGN KEY ("entry_id") REFERENCES "toolbox" ("id"));
CREATE INDEX "toolboxtag_entry_id" ON "toolboxtag" ("entry_id");
CREATE TABLE "toolboxsignature" ("id" INTEGER NOT NULL PRIMARY KEY, "toolbox_id" INTEGER NOT NULL, "signature_id" INTEGER NOT NULL, FOREIGN KEY ("toolbox_id") REFERENCES "toolbox" ("id"), FOREIGN KEY ("signature_id") REFERENCES "signature" ("id") ON DELETE CASCADE);
CREATE INDEX "toolboxsignature_toolbox_id" ON "toolboxsignature" ("toolbox_id");
CREATE UNIQUE INDEX "toolboxsignature_signature_id" ON "toolboxsignature" ("signature_id");
CREATE TABLE "toolboxvar" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "type" VARCHAR(255) NOT NULL, "label" VARCHAR(255), "description" TEXT, "optional" INTEGER NOT NULL, "default" VARCHAR(255), "min" REAL, "max" REAL, "step" REAL, "values" VARCHAR(255), "toolbox_id" INTEGER NOT NULL, FOREIGN KEY ("toolbox_id") REFERENCES "toolbox" ("id"));
CREATE INDEX "toolboxvar_toolbox_id" ON "toolboxvar" ("toolbox_id");
CREATE TABLE "toolboxdependency" ("id" INTEGER NOT NULL PRIMARY KEY, "type" VARCHAR(255) NOT NULL, "identifier" VARCHAR(255) NOT NULL, "version" VARCHAR(255), "repository" VARCHAR(255), "toolbox_id" INTEGER NOT NULL, FOREIGN KEY ("toolbox_id") REFERENCES "toolbox" ("id"));
CREATE INDEX "toolboxdependency_toolbox_id" ON "toolboxdependency" ("toolbox_id");
CREATE TABLE "userroles" ("id" INTEGER NOT NULL PRIMARY KEY, "user_id" INTEGER NOT NULL, "role_id" INTEGER NOT NULL, FOREIGN KEY ("user_id") REFERENCES "user" ("id"), FOREIGN KEY ("role_id") REFERENCES "role" ("id"));
CREATE INDEX "userroles_user_id" ON "userroles" ("user_id");
CREATE INDEX "userroles_role_id" ON "userroles" ("role_id");
CREATE UNIQUE INDEX "userroles_user_id_role_id" ON "userroles" ("user_id", "role_id");
CREATE VIRTUAL TABLE "problemindex" USING FTS4 ("name" TEXT NOT NULL, "description" TEXT NOT NULL, "problem_id" INTEGER NOT NULL, FOREIGN KEY ("problem_id") REFERENCES "problem" ("id"));
CREATE TABLE 'problemindex_content'(docid INTEGER PRIMARY KEY, 'c0name', 'c1description', 'c2problem_id', 'c3FOREIGN');
CREATE TABLE 'problemindex_segments'(blockid INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE 'problemindex_segdir'(level INTEGER,idx INTEGER,start_block INTEGER,leaves_end_block INTEGER,end_block INTEGER,root BLOB,PRIMARY KEY(level, idx));
CREATE TABLE 'problemindex_docsize'(docid INTEGER PRIMARY KEY, size BLOB);
CREATE TABLE 'problemindex_stat'(id INTEGER PRIMARY KEY, value BLOB);
CREATE VIRTUAL TABLE "solutionindex" USING FTS4 ("name" TEXT NOT NULL, "description" TEXT NOT NULL, "solution_id" INTEGER NOT NULL, FOREIGN KEY ("solution_id") REFERENCES "solution" ("id"));
CREATE TABLE 'solutionindex_content'(docid INTEGER PRIMARY KEY, 'c0name', 'c1description', 'c2solution_id', 'c3FOREIGN');
CREATE TABLE 'solutionindex_segments'(blockid INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE 'solutionindex_segdir'(level INTEGER,idx INTEGER,start_block INTEGER,leaves_end_block INTEGER,end_block INTEGER,root BLOB,PRIMARY KEY(level, idx));
CREATE TABLE 'solutionindex_docsize'(docid INTEGER PRIMARY KEY, size BLOB);
CREATE TABLE 'solutionindex_stat'(id INTEGER PRIMARY KEY, value BLOB);
CREATE VIRTUAL TABLE "toolboxindex" USING FTS4 ("name" TEXT NOT NULL, "description" TEXT NOT NULL, "toolbox_id" INTEGER NOT NULL, FOREIGN KEY ("toolbox_id") REFERENCES "toolbox" ("id"));
CREATE TABLE 'toolboxindex_content'(docid INTEGER PRIMARY KEY, 'c0name', 'c1description', 'c2toolbox_id', 'c3FOREIGN');
CREATE TABLE 'toolboxindex_segments'(blockid INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE 'toolboxindex_segdir'(level INTEGER,idx INTEGER,start_block INTEGER,leaves_end_block INTEGER,end_block INTEGER,root BLOB,PRIMARY KEY(level, idx));
CREATE TABLE 'toolboxindex_docsize'(docid INTEGER PRIMARY KEY, size BLOB);
CREATE TABLE 'toolboxindex_stat'(id INTEGER PRIMARY KEY, value BLOB);
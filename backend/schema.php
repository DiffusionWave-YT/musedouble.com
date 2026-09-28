<?php
declare(strict_types=1);
function install_schema(): void {
    foreach (['workflows', 'jobs', 'results', 'sessions'] as $dir) if (!is_dir(data_dir() . '/' . $dir)) mkdir(data_dir() . '/' . $dir, 0700, true);
    db()->exec("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT NOT NULL COLLATE NOCASE UNIQUE,email TEXT COLLATE NOCASE UNIQUE,name TEXT NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'member',can_generate INTEGER NOT NULL DEFAULT 0,active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS settings(name TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS models(id TEXT PRIMARY KEY,name TEXT NOT NULL,character_prompt TEXT NOT NULL,eye_prompt TEXT NOT NULL,loras TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS workflows(mode TEXT PRIMARY KEY,filename TEXT NOT NULL,metadata TEXT NOT NULL,updated_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),mode TEXT NOT NULL,model_id TEXT NOT NULL,model_name TEXT NOT NULL,status TEXT NOT NULL,prompt_id TEXT,server TEXT NOT NULL,options TEXT NOT NULL,error TEXT,request_key TEXT NOT NULL,created_at INTEGER NOT NULL,UNIQUE(user_id,request_key));
    CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY,job_id TEXT NOT NULL REFERENCES jobs(id),user_id INTEGER NOT NULL REFERENCES users(id),output_index INTEGER NOT NULL,filename TEXT NOT NULL,mime TEXT NOT NULL,created_at INTEGER NOT NULL,UNIQUE(job_id,output_index));
    CREATE TABLE IF NOT EXISTS attempts(ip TEXT NOT NULL,identity TEXT NOT NULL,created_at INTEGER NOT NULL);
    CREATE INDEX IF NOT EXISTS attempts_time ON attempts(created_at);
    CREATE INDEX IF NOT EXISTS jobs_user ON jobs(user_id,created_at);");
    if (setting('generation') === null) put_setting('generation', ['max_batch' => 2, 'ratios' => [['label' => '4:5', 'width' => 1024, 'height' => 1280], ['label' => '5:4', 'width' => 1280, 'height' => 1024], ['label' => '1:1', 'width' => 1024, 'height' => 1024], ['label' => '9:16', 'width' => 720, 'height' => 1280], ['label' => '16:9', 'width' => 1280, 'height' => 720]]]);
}

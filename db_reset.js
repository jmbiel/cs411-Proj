// Load config file
var config = JSON.parse(cat("db_config.json"))

// Drop Repo
db = new Mongo().getDB(config.repo.name)
db.dropDataBase()
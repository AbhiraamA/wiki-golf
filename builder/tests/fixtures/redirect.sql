-- MySQL dump (Wiki Golf test fixture)

DROP TABLE IF EXISTS `redirect`;
CREATE TABLE `redirect` (
  `rd_from` int(8) unsigned NOT NULL DEFAULT 0,
  `rd_namespace` int(11) NOT NULL DEFAULT 0,
  `rd_title` varbinary(255) NOT NULL DEFAULT '',
  `rd_interwiki` varbinary(32) DEFAULT NULL,
  `rd_fragment` varbinary(255) DEFAULT NULL,
  PRIMARY KEY (`rd_from`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;

INSERT INTO `redirect` VALUES (21,0,'Octopus','',''),(22,0,'Apollo_11','',''),(23,0,'Cephalopoda','',''),(24,0,'Cephalopod','',''),(25,0,'Cephalopods','',''),(27,0,'Moon','',''),(28,0,'Jules_Verne','',''),(26,0,'Squid','enwiki','');

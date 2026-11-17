-- MySQL dump (Wiki Golf test fixture)

DROP TABLE IF EXISTS `page`;
CREATE TABLE `page` (
  `page_id` int(8) unsigned NOT NULL AUTO_INCREMENT,
  `page_namespace` int(11) NOT NULL DEFAULT 0,
  `page_title` varbinary(255) NOT NULL DEFAULT '',
  `page_is_redirect` tinyint(1) unsigned NOT NULL DEFAULT 0,
  `page_is_new` tinyint(1) unsigned NOT NULL DEFAULT 0,
  `page_random` double unsigned NOT NULL DEFAULT 0,
  `page_touched` binary(14) NOT NULL,
  `page_links_updated` binary(14) DEFAULT NULL,
  `page_latest` int(8) unsigned NOT NULL DEFAULT 0,
  `page_len` int(8) unsigned NOT NULL DEFAULT 0,
  `page_content_model` varbinary(32) DEFAULT NULL,
  `page_lang` varbinary(35) DEFAULT NULL,
  PRIMARY KEY (`page_id`),
  UNIQUE KEY `page_name_title` (`page_namespace`,`page_title`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;

/*!40000 ALTER TABLE `page` DISABLE KEYS */;
INSERT INTO `page` VALUES
(1,0,'Octopus',0,0,0.5,'20261001000000','20261001000000',5001,9000,'wikitext',NULL),
(2,0,'Squid',0,0,0.5,'20261001000000','20261001000000',5002,8000,'wikitext',NULL),
(3,0,'Nautilus',0,0,0.5,'20261001000000','20261001000000',5003,7000,'wikitext',NULL),
(4,0,'Cephalopod',0,0,0.5,'20261001000000','20261001000000',5004,9000,'wikitext',NULL),
(5,0,'Camouflage',0,0,0.5,'20261001000000','20261001000000',5005,6000,'wikitext',NULL),
(6,0,'Giant_squid',0,0,0.5,'20261001000000','20261001000000',5006,6000,'wikitext',NULL),
(7,0,'Twenty_Thousand_Leagues_Under_the_Seas',0,0,0.5,'20261001000000','20261001000000',5007,9000,'wikitext',NULL),
(8,0,'Jules_Verne',0,0,0.5,'20261001000000','20261001000000',5008,9000,'wikitext',NULL),
(9,0,'Science_fiction',0,0,0.5,'20261001000000','20261001000000',5009,9000,'wikitext',NULL),
(10,0,'From_the_Earth_to_the_Moon',0,0,0.5,'20261001000000','20261001000000',5010,7000,'wikitext',NULL),
(11,0,'Moon',0,0,0.5,'20261001000000','20261001000000',5011,12000,'wikitext',NULL),
(12,0,'Apollo_11',0,0,0.5,'20261001000000','20261001000000',5012,12000,'wikitext',NULL),
(13,0,'Mollusca',0,0,0.5,'20261001000000','20261001000000',5013,7000,'wikitext',NULL),
(14,0,'Ocean',0,0,0.5,'20261001000000','20261001000000',5014,9000,'wikitext',NULL),
(15,0,'List_of_cephalopods',0,0,0.5,'20261001000000','20261001000000',5015,8000,'wikitext',NULL),
(16,0,'1969',0,0,0.5,'20261001000000','20261001000000',5016,9000,'wikitext',NULL),
(17,0,'July_20',0,0,0.5,'20261001000000','20261001000000',5017,6000,'wikitext',NULL),
(18,0,'Mercury_(planet,_element)',0,0,0.5,'20261001000000','20261001000000',5018,3000,'wikitext',NULL),
(19,0,'Earth',0,0,0.5,'20261001000000','20261001000000',5019,12000,'wikitext',NULL),
(20,0,'Stub',0,0,0.5,'20261001000000','20261001000000',5020,40,'wikitext',NULL),
(21,0,'Octopi',1,0,0.5,'20261001000000','20261001000000',5021,20,'wikitext',NULL),
(22,0,'Apollo_eleven',1,0,0.5,'20261001000000','20261001000000',5022,20,'wikitext',NULL),
(23,0,'Cephalopods',1,0,0.5,'20261001000000','20261001000000',5023,20,'wikitext',NULL),
(24,0,'Cephalopoda',1,0,0.5,'20261001000000','20261001000000',5024,20,'wikitext',NULL),
(25,0,'Triple_redirect',1,0,0.5,'20261001000000','20261001000000',5025,20,'wikitext',NULL),
(26,1,'Octopus',0,0,0.5,'20261001000000','20261001000000',5026,500,'wikitext',NULL),
(27,0,'Luna',1,0,0.5,'20261001000000','20261001000000',5027,20,'wikitext',NULL),
(28,0,'Verne\'s_Moon',1,0,0.5,'20261001000000','20261001000000',5028,20,'wikitext',NULL);
/*!40000 ALTER TABLE `page` ENABLE KEYS */;

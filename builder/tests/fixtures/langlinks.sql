-- MySQL dump (Wiki Golf test fixture)

DROP TABLE IF EXISTS `langlinks`;
CREATE TABLE `langlinks` (
  `ll_from` int(8) unsigned NOT NULL DEFAULT 0,
  `ll_lang` varbinary(35) NOT NULL DEFAULT '',
  `ll_title` varbinary(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`ll_from`,`ll_lang`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;

INSERT INTO `langlinks` VALUES
(1,'en','Octopus'),(1,'fr','Pieuvre'),(1,'de','Kraken'),(1,'es','Octopoda'),
(2,'en','Squid'),
(3,'en','Nautilus'),
(4,'en','Cephalopod'),(4,'fr','Céphalopode'),(4,'de','Kopffüßer'),
(5,'en','Crypsis'),
(6,'en','Giant squid'),
(7,'en','Twenty Thousand Leagues Under the Seas'),
(8,'en','Jules Verne'),(8,'fr','Jules Verne'),
(9,'en','Science fiction'),(9,'fr','Science-fiction'),(9,'de','Science-Fiction'),
(10,'en','From the Earth to the Moon'),
(11,'en','Moon'),(11,'fr','Lune'),(11,'de','Mond'),(11,'es','Luna'),(11,'it','Luna'),(11,'ja','月'),(11,'zh','月球'),
(12,'en','Apollo 11'),(12,'fr','Apollo 11'),
(13,'en','Mollusca'),
(14,'en','Ocean'),(14,'fr','Océan'),(14,'de','Meer'),(14,'es','Océano'),(14,'it','Oceano'),
(15,'en','List of cephalopods'),
(19,'en','Earth'),(19,'fr','Terre'),(19,'de','Erde'),(19,'es','Tierra'),(19,'it','Terra'),(19,'ja','地球'),
(20,'en','Stub');

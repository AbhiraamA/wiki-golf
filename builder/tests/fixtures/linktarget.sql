-- MySQL dump (Wiki Golf test fixture)

DROP TABLE IF EXISTS `linktarget`;
CREATE TABLE `linktarget` (
  `lt_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `lt_namespace` int(11) NOT NULL,
  `lt_title` varbinary(255) NOT NULL,
  PRIMARY KEY (`lt_id`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;

INSERT INTO `linktarget` VALUES (100,0,'Squid'),(101,0,'Nautilus'),(102,0,'Cephalopods'),(103,0,'Camouflage'),(104,0,'Ocean'),(105,0,'Octopi'),(106,0,'Mollusca'),(107,0,'Giant_squid'),(108,0,'Cephalopod'),(109,0,'Triple_redirect'),(110,0,'Twenty_Thousand_Leagues_Under_the_Seas'),(111,0,'Verne\'s_Moon');
INSERT INTO `linktarget` VALUES (112,0,'Octopus'),(113,0,'Jules_Verne'),(114,0,'From_the_Earth_to_the_Moon'),(115,0,'Science_fiction'),(116,0,'Moon'),(117,0,'Luna'),(118,0,'Nonexistent_page'),(119,0,'Apollo_11'),(120,0,'Earth'),(121,0,'1969'),(122,0,'July_20'),(123,1,'Octopus'),(124,0,'Unused_target');

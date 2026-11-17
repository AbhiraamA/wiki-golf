-- MySQL dump (Wiki Golf test fixture)

DROP TABLE IF EXISTS `page_props`;
CREATE TABLE `page_props` (
  `pp_page` int(10) unsigned NOT NULL,
  `pp_propname` varbinary(60) NOT NULL DEFAULT '',
  `pp_value` blob NOT NULL,
  `pp_sortkey` float DEFAULT NULL,
  PRIMARY KEY (`pp_page`,`pp_propname`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;

INSERT INTO `page_props` VALUES
(18,'disambiguation','',NULL),
(1,'wikibase_item','Q1',NULL),
(12,'page_image_free','Apollo_11_(photo).jpg',NULL);

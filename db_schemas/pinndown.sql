CREATE DATABASE  IF NOT EXISTS `pinn` /*!40100 DEFAULT CHARACTER SET utf8 */;
USE `pinn`;
-- MySQL dump 10.13  Distrib 5.6.15, for Win64 (x86_64)
--
-- Host: localhost    Database: pinn
-- ------------------------------------------------------
-- Server version	5.6.15-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `events`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `events` (
  `id` int(10) unsigned NOT NULL,
  `date` datetime NOT NULL,
  `sporttype` varchar(50) DEFAULT NULL,
  `league` varchar(255) DEFAULT NULL,
  `islive` bit(1) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `events1` (`sporttype`,`date`,`id`),
  KEY `events2` (`date`,`id`),
  KEY `events3` (`date`,`islive`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary table structure for view `gamesdenorm`
--

SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE TABLE `gamesdenorm` (
  `evid` tinyint NOT NULL,
  `evdate` tinyint NOT NULL,
  `sporttype` tinyint NOT NULL,
  `league` tinyint NOT NULL,
  `islive` tinyint NOT NULL,
  `pahnameraw` tinyint NOT NULL,
  `pahpitcher` tinyint NOT NULL,
  `pahname` tinyint NOT NULL,
  `pavnameraw` tinyint NOT NULL,
  `pavpitcher` tinyint NOT NULL,
  `pavname` tinyint NOT NULL,
  `penumber` tinyint NOT NULL,
  `pedesc` tinyint NOT NULL,
  `threshold` tinyint NOT NULL,
  `bettype` tinyint NOT NULL,
  `bettypehr` tinyint NOT NULL,
  `hprice` tinyint NOT NULL,
  `dprice` tinyint NOT NULL,
  `vprice` tinyint NOT NULL,
  `betlimit` tinyint NOT NULL,
  `snapshotdate` tinyint NOT NULL,
  `opening` tinyint NOT NULL,
  `latest` tinyint NOT NULL,
  `hid` tinyint NOT NULL,
  `did` tinyint NOT NULL,
  `vid` tinyint NOT NULL
) ENGINE=MyISAM */;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `odds`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `odds` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `eventid` int(10) unsigned NOT NULL,
  `periodnumber` tinyint(3) unsigned DEFAULT NULL,
  `contestantnum` int(10) unsigned DEFAULT NULL,
  `rotnum` mediumint(8) unsigned DEFAULT NULL,
  `snapshotdate` datetime NOT NULL,
  `type` char(1) CHARACTER SET latin1 NOT NULL,
  `vhdou` char(1) CHARACTER SET latin1 DEFAULT NULL,
  `threshold` decimal(6,3) DEFAULT NULL,
  `price` float NOT NULL,
  `to_base` float DEFAULT NULL,
  `opening` tinyint(3) unsigned DEFAULT NULL,
  `latest` tinyint(3) unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `eventid` (`eventid`,`periodnumber`,`snapshotdate`,`type`,`vhdou`,`threshold`),
  KEY `odds1` (`snapshotdate`,`type`),
  KEY `odds2` (`type`)
) ENGINE=InnoDB AUTO_INCREMENT=15446 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `participants`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `participants` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `eventid` int(10) unsigned NOT NULL,
  `contestantnum` int(10) unsigned NOT NULL,
  `rotnum` mediumint(8) unsigned NOT NULL,
  `vhdou` char(1) CHARACTER SET latin1 DEFAULT NULL,
  `name` varchar(200) NOT NULL,
  `pitcher` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `eventid` (`eventid`,`contestantnum`,`rotnum`),
  KEY `participants1` (`eventid`,`vhdou`),
  KEY `participants2` (`name`),
  KEY `participants3` (`vhdou`,`eventid`)
) ENGINE=InnoDB AUTO_INCREMENT=7710 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `periods`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `periods` (
  `id` mediumint(8) unsigned NOT NULL AUTO_INCREMENT,
  `eventid` int(10) unsigned NOT NULL,
  `number` tinyint(3) unsigned NOT NULL,
  `description` varchar(25) NOT NULL,
  `cutoff` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `eventid` (`eventid`,`number`),
  KEY `periods1` (`number`)
) ENGINE=InnoDB AUTO_INCREMENT=2666 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `snapshots`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `snapshots` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `eventid` int(10) unsigned NOT NULL,
  `periodnumber` tinyint(3) unsigned DEFAULT NULL,
  `date` datetime NOT NULL,
  `systemdate` datetime NOT NULL,
  `status` char(1) CHARACTER SET latin1 DEFAULT NULL,
  `upd` varchar(20) DEFAULT NULL,
  `spreadmax` mediumint(8) unsigned DEFAULT NULL,
  `mlmax` mediumint(8) unsigned DEFAULT NULL,
  `totalmax` mediumint(8) unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `eventid` (`eventid`,`periodnumber`,`date`)
) ENGINE=InnoDB AUTO_INCREMENT=5311 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Final view structure for view `gamesdenorm`
--

/*!50001 DROP TABLE IF EXISTS `gamesdenorm`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `gamesdenorm` AS select `ev`.`id` AS `evid`,`ev`.`date` AS `evdate`,`ev`.`sporttype` AS `sporttype`,`ev`.`league` AS `league`,`ev`.`islive` AS `islive`,`pah`.`name` AS `pahnameraw`,`pah`.`pitcher` AS `pahpitcher`,(case when isnull(`pah`.`pitcher`) then `pah`.`name` else concat(`pah`.`name`,' (',`pah`.`pitcher`,')') end) AS `pahname`,`pav`.`name` AS `pavnameraw`,`pav`.`pitcher` AS `pavpitcher`,(case when isnull(`pav`.`pitcher`) then `pav`.`name` else concat(`pav`.`name`,' (',`pav`.`pitcher`,')') end) AS `pavname`,`pe`.`number` AS `penumber`,`pe`.`description` AS `pedesc`,`odh`.`threshold` AS `threshold`,`odh`.`type` AS `bettype`,(case `odh`.`type` when 'm' then 'moneyline' when 't' then 'total' when 's' then 'spread' end) AS `bettypehr`,`odh`.`price` AS `hprice`,`odd`.`price` AS `dprice`,`odv`.`price` AS `vprice`,(case `odh`.`type` when 'm' then `sn`.`mlmax` when 's' then `sn`.`spreadmax` when 't' then `sn`.`totalmax` end) AS `betlimit`,`odh`.`snapshotdate` AS `snapshotdate`,`odh`.`opening` AS `opening`,`odh`.`latest` AS `latest`,`odh`.`id` AS `hid`,`odd`.`id` AS `did`,`odv`.`id` AS `vid` from ((((((((`events` `ev` join `participants` `pah` on(((`pah`.`eventid` = `ev`.`id`) and (`pah`.`vhdou` = 'h')))) join `participants` `pav` on(((`pav`.`eventid` = `ev`.`id`) and (`pav`.`vhdou` = 'v')))) join `periods` `pe` on((`pe`.`eventid` = `ev`.`id`))) join `odds` `odh` on(((`odh`.`eventid` = `ev`.`id`) and (`odh`.`periodnumber` = `pe`.`number`) and (`odh`.`type` = `odh`.`type`) and (`pah`.`contestantnum` = `odh`.`contestantnum`) and (`pah`.`rotnum` = `odh`.`rotnum`)))) join `odds` `odv` on(((`odv`.`eventid` = `ev`.`id`) and (`odv`.`periodnumber` = `pe`.`number`) and (`odv`.`type` = `odh`.`type`) and (`pav`.`contestantnum` = `odv`.`contestantnum`) and (`pav`.`rotnum` = `odv`.`rotnum`) and (`odv`.`snapshotdate` = `odh`.`snapshotdate`)))) join `snapshots` `sn` on(((`sn`.`eventid` = `ev`.`id`) and (`sn`.`periodnumber` = `odh`.`periodnumber`) and (`sn`.`date` = `odh`.`snapshotdate`)))) left join `participants` `pad` on(((`pad`.`eventid` = `ev`.`id`) and (`pad`.`vhdou` = 'd') and (`odh`.`type` = 'm')))) left join `odds` `odd` on(((`odd`.`eventid` = `ev`.`id`) and (`odd`.`periodnumber` = `pe`.`number`) and (`odd`.`type` = `odh`.`type`) and (`odd`.`snapshotdate` = `odh`.`snapshotdate`) and (`pad`.`contestantnum` = `odd`.`contestantnum`) and (`pad`.`rotnum` = `odd`.`rotnum`)))) where (((isnull(`pad`.`id`) and isnull(`odd`.`id`)) or ((`pad`.`id` is not null) and (`odd`.`id` is not null))) and ((case `odh`.`type` when 'm' then `sn`.`mlmax` when 's' then `sn`.`spreadmax` when 't' then `sn`.`totalmax` end) > 0)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2015-03-07 13:44:54

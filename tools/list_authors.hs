-- Copyright (C) 2004 David Roundy
--
-- This program is free software; you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation; either version 2, or (at your option)
-- any later version.
--
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
--
-- You should have received a copy of the GNU General Public License
-- along with this program;  see the file COPYING.  If not, write to
-- the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
-- Boston, MA 02110-1301, USA.

module Main (main) where

import Darcs.Utils ( formatPath )
import Darcs.Repository ( withRepository, read_repo, ($-) )
import Darcs.Patch.Info ( pi_author )
import Darcs.Hopefully ( info )
import Darcs.Ordered ( mapRL, concatRL )

import Data.List ( sort, group )
import System ( getProgName, getArgs )

intro :: Bool -> IO String
intro do_stats = do
  prog_name <- getProgName
  return $
    "This is a list of ALL contributors to darcs, sorted according to the\n"++
    "number of patches they have contributed.  This list is automatically\n"++
    "created from the darcs repository, so if there are problems with it,\n"++
    "changes should be made to list_authors.hs.\n"++
    "\n" ++
    (if do_stats
     then ""
     else ("Run " ++ formatPath (prog_name ++ " stats") ++
           " for more detailed information.\n" ++ "\n"))

main :: IO ()
main = withRepository [] $- \repository ->
       do darcs_history <- read_repo repository
          use_statistics <- elem "stats" `fmap` getArgs
          intro use_statistics >>= putStr
          mapM_ putStrLn $ sort_authors use_statistics $ mapRL (pi_author.info)
                         $ concatRL darcs_history

droundy :: String
droundy = "David Roundy <droundy@darcs.net>"

-- contributers with more than 2 addresses 
gwern_branwen,
  marnix_klooster, eric_kow, andres_loeh,
  simon_marlow, pekka_pessi,
  erik_schnetter, don_stewart,
  edwin_thomson, mark_stosberg,
  thomas_zander, tomasz_zielonka, lele_gaifax , christian_kellermann :: String
marnix_klooster = "Marnix Klooster <marnix.klooster@gmail.com>"
eric_kow        = "Eric Kow <kowey@darcs.net>"
andres_loeh     = "Andres Loeh <mail@andres-loeh.de>"
simon_marlow    = "Simon Marlow <simonmar@microsoft.com>"
erik_schnetter  = "Erik Schnetter <schnetter@cct.lsu.edu>"
don_stewart     = "Don Stewart <dons@galois.com>"
gwern_branwen   = "Gwern Branwen <gwern0@gmail.com>"
pekka_pessi     = "Pekka Pessi <pekka.pessi@nokia.com>"
mark_stosberg   = "Mark Stosberg <mark@summersault.com>"
edwin_thomson   = "Edwin Thomson <edwin.thomson@businesswebsoftware.com>"
thomas_zander   = "Thomas Zander <zander@kde.org>"
tomasz_zielonka = "Tomasz Zielonka <tomasz.zielonka@gmail.com>"
lele_gaifax     = "Lele Gaifax <lele@nautilus.homeip.net>"
christian_kellermann = "Christian Kellermann <Christian.Kellermann@nefkom.net>"

-- contributers who only provided an email address, one for which we know the name
-- note that having an entry in this table counts as two addresses... so if there 
-- another address used besides this entry, you should remove it from the table,
-- add a constant (above) and modify canonize_authors (below)
authors_sans_name :: [ (String, String) ]
authors_sans_name =
  [ ("adam@megacz.com"         , "Adam Megacz")        
  , ("aj@azure.humbug.org.au"  , "Anthony Towns") 
  , ("andrew@pimlott.net"      , "Andrew Pimlott")
  , ("andrew@siaris.net"       , "Andrew L Johnson")
  , ("aoiko@cc.ece.ntua.gr"    , "Aggelos Economopoulos")
  , ("ben.franksen@online.de"  , "Benjamin Franksen")
  , ("brian@brianweb.net"      , "Brian Alliet")
  , ("chevalier@alum.wellesley.edu", "Kirsten Chevalier")
  , ("chucky@dtek.chalmers.se" , "Anders Hockersten")
  , ("dgorin@dc.uba.ar"        , "Daniel Gorin")
  , ("dbindner@truman.edu"     , "Don Bindner")
  , ("egli@apache.org"         , "Christian Egli")
  , ("ei@vuokko.info"          , "Esa Ilari Vuokko")
  , ("era+darcs@iki.fi"        , "Era Eriksson")
  , ("eric@rti-zone.org"       , "Eric Gaudet")
  , ("florent.becker@ens-lyon.org", "Florent Becker")
  , ("forge@dr.ea.ms"          , "Andrew J. Kroll")
  , ("fw@deneb.enyo.de"        , "Florian Weimer")
  , ("gaetan.lehmann@jouy.inra.fr", "Gaetan Lehmann")
  , ("glaweh@physik.fu-berlin.de", "Henning Glawe")
  , ("ijones@debian.org"       , "Isaac Jones")
  , ("jan@informatik.unibw-muenchen.de", "Jan Scheffczyk") 
  , ("janbraun@gmx.net"        , "Jan Braun")
  , ("jani@iv.ro"              , "Jani Monoses")
  , ("jch@pps.jussieu.fr"      , "Juliusz Chroboczek" )
  , ("jemfinch@supybot.com"    , "Jeremy Fincher")
  , ("joe@elem.com"            , "Joe Edmonds")
  , ("kannan@cakoose.com"      , "Kannan Goundan")
  , ("ketil@ii.uib.no"         , "Ketil Malde")
  , ("kili@outback.escape.de"  , "Matthias Kilian")
  , ("lord@crocodile.org"      , "Vadim Zaliva")
  , ("malebria@riseup.net"     , "Marco Tulio Gontijo e Silva")
  , ("me@JonathonMah.com"      , "Jonathon Mah")
  , ("me@mornfall.net"         , "Petr Rockai")
  , ("naesten@myrealbox.com"   , "Samuel Bronson")
  , ("naur@post11.tele.dk"     , "Thorkil Naur")
  , ("nicolas.pouillard@gmail.com" , "Nicolas Pouillard")
  , ("nils@ndecker.de"         , "Nils Decker")
  , ("nwf@cs.jhu.edu"          , "Nathaniel Filardo")
  , ("peter.maxwell@anu.edu.au", "Peter Maxwell")
  , ("peter@syncad.com"        , "Peter Hercek")
  , ("peter@zarquon.se"        , "Peter Strand")
  , ("petersen@haskell.org"    , "Jens Petersson") 
  , ("ptp@lysator.liu.se"      , "Tommy Pettersson")
  , ("ralph@inputplus.co.uk"   , "Ralph Corderoy")
  , ("rho@swiftdsl.com.au"     , "Nigel Rowe")
  , ("schaffner@gmx.li"        , "Martin Schaffner")
  , ("schwern@pobox.com"       , "Michael G Schwern")
  , ("sean.robinson@sccmail.maricopa.edu", "Sean Robinson")
  , ("ser@germane-software.com", "Sean Russell")
  , ("shae@ScannedInAvian.com" , "Shae Erisson")  
  , ("simon@joyful.com"        , "Simon Michael")
  , ("simons@cryp.to"          , "Peter Simons")
  , ("smithbone@gmail.com"     , "Richard Smith")
  , ("sreindl@triobit.de"      , "Stephen Reindl")
  , ("thies@thieso.net"        , "Thies C. Arntzen")
  , ("thomas_bevan@toll.com.au", "Thomas L. Bevan")
  , ("tux_rocker@reinier.de"   , "Reinier Lamers")
  , ("trivee@noir.crocodile.org", "Vladimir Vysotsky")
  , ("v.haisman@sh.cvut.cz"    , "Vaclav Haisman") 
  , ("vborja@thehatcher.com"   , "Victor Hugo Borja Rodriguez")
  , ("wnoise@ofb.net"          , "Aaron Denney")
  , ("xhl178@shaw.ca"          , "Randy Roesler") 
  , ("zooko@zooko.com"         , "Bryce Wilcox-O'Hearn")
-- CUSTOMISE FOR ZWIKI, 1. authors just missing the name
  ,("bob+zwiki@mcelrath.org"   , "Bob McElrath")
  ,("lele@seldati.it"          , "Lele Gaifax")
  ,("nachtigall@web.de"        , "Jens Nachtigall")
  ,("frank@laurijssens.nl"     , "Frank Laurijssens")
  ,("foenyx@online.fr"         , "Nicolas Laurent")
  ,("stefan.rank@oefai.at"     , "Stefan Rank")
  ,("tcchou@tcchou.org"        , "T. C. Chou")
  ,("stefan.rank@ofai.at"      , "Stefan Rank")
  ,("bill.page1@sympatico.ca"  , "Bill Page")
  ,("riley@uic.com"            , "John Riley")
  ,("jbb@contradix.com"        , "Jordan Baker")
  ,("alvaro@antalia.com"       , "Alvaro Cantero")
  ,("betabug.darcs@betabug.ch" , "Sascha Welter")
  ,("klippe@pf.pl"             , "Jakub Wiśniowski")
  ,("vejeta@gmail.com"         , "Juan Manuel Méndez Rey")
  ,("m.pedersen@icelus.org"    , "Michael Pedersen")
  ,("huron@sopinspace.com"     , "Raphaël Badin")
  ,("an.ma@web.de"             , "Andreas Mayer")
-- END
 ]  

canonize_author :: String -> String
-- CUSTOMISE FOR ZWIKI, 2: more complex cases:
canonize_author a
    | a `elem` [
       "simon@joyful.com"
      ,"simon@blue"
      ,"root <simon@joyful.com>"
      ,"Simon Michael <simon@dynabook.joyful.com>"
      ] = "Simon Michael <simon@joyful.com>"
    | a `elem` [
       "encolpe.degoute@ingeniweb.com"
      ,"    darcs sendencolpe.degoute@colpi.info"
      ] = "Encolpe Degoute <encolpe.degoute@ingeniweb.com>"
-- END
canonize_author "David" = droundy
canonize_author "Tomasz Zielonka <t.zielonka@students.mimuw.edu.pl>" = tomasz_zielonka
canonize_author "Tomasz Zielonka <tomekz@gemius.pl>" = tomasz_zielonka
canonize_author "zander@kde.org" = thomas_zander 
canonize_author "mail@andres-loeh.de" = andres_loeh
canonize_author "Andres Loeh <andres@cs.uu.nl>" = andres_loeh
canonize_author "Andres Loeh <loeh@iai.uni-bonn.de>" = andres_loeh
canonize_author "Benedikt Schmidt <beschmi@cloaked.de>" = "Benedikt Schmidt <benedikt.schmidt@inf.ethz.ch>"
canonize_author "benjamin.franksen@bessy.de" = "Benjamin Franksen <ben.franksen@online.de>"
canonize_author "Lennart Kolmodin <kolmodin@dtek.chalmers.se>" = "Lennart Kolmodin <kolmodin@gentoo.org>"
canonize_author "dons@cse.unsw.edu.au" = don_stewart
canonize_author "kow@loria.fr" = eric_kow
canonize_author "Eric Kow <eric.kow@gmail.com>" = eric_kow
canonize_author "Eric Kow <eric.kow@loria.fr>" = eric_kow
canonize_author "Eric Kow <E.Y.Kow@brighton.ac.uk>" = eric_kow
canonize_author "schnetter@aei.mpg.de" = erik_schnetter
canonize_author "Erik Schnetter <schnetter@aei.mpg.de>" = erik_schnetter
canonize_author "edwin.thomson@businesswebsoftware.com" = edwin_thomson
canonize_author "edwin.thomson@gmail.com" = edwin_thomson
canonize_author "Kirill Smelkov <kirr@mns.spb.ru>" = "Kirill Smelkov <kirr@landau.phys.spbu.ru>"
canonize_author "mark@summersault.com" = mark_stosberg
canonize_author "jvr+darcs@blub.net" = "Joeri van Ruth <jvr@blub.net>"
canonize_author "testerALL --ignore-times" = mark_stosberg
canonize_author "lele@seldati.it" = lele_gaifax
canonize_author "lele@nautilus.homeip.net" = lele_gaifax
canonize_author "gwern0@gmail.com" = gwern_branwen
canonize_author "Trent W. Buck <twb@cyber.com.au>" = "Trent W. Buck <trentbuck@gmail.com>"
canonize_author "Pekka.Pessi@nokia.com" = pekka_pessi
canonize_author "Pekka Pessi <first.last@nokia.com>" = pekka_pessi
canonize_author "Pekka Pessi <ppessi@gmail.com>"     = pekka_pessi
canonize_author "Pekka Pessi <pekka@pessi.fi>"       = pekka_pessi
canonize_author "Simon Marlow <marlowsd@gmail.com>"  = simon_marlow
canonize_author "Spencer Janssen <sjanssen@cse.unl.edu>" = "Spencer Janssen <spencerjanssen@gmail.com>"
canonize_author "" = gwern_branwen
canonize_author s
    | s `contains` "roundy" = droundy
    | s `contains` "igloo" = "Ian Lynagh <igloo@earth.li>"
    | s `contains` "Thomas Zander" = thomas_zander
    | s `contains` "marnix.klooster@" = marnix_klooster
    | s `contains` "marnix_klooster" = marnix_klooster
    | s `contains` "mklooster@baan.nl" = marnix_klooster
    | s `contains` "mirian@" = "Mirian Crzig Lennox <mirian@cosmic.com>"
    | s `contains` "zbrown" = "Zack Brown <zbrown@tumblerings.org>"
    | s `contains` "daniel.buenzli@epfl.ch" = "Daniel Buenzli <daniel.buenzli@epfl.ch>" -- avoid an accent
    | s `contains` "Kellermann" = christian_kellermann
canonize_author s =
  if (not.null) eaLst 
      then (uncurry add_name_to_mail) $ head eaLst
      else s
  where eaLst = [ ea | ea <- authors_sans_name, fst ea == s ]

sort_authors :: Bool -> [String] -> [String]
sort_authors use_stats as = reverse $ map shownames $ sort $
                            map (\s -> (length s,head s)) $
                            group $ sort $ map canonize_author as
        where shownames (n, a) = if use_stats
                                 then show n ++ "\t" ++ a
                                 else a

contains :: String -> String -> Bool
a `contains` b | length a < length b = False
               | take (length b) a == b = True
               | otherwise = tail a `contains` b

add_name_to_mail :: String -> String -> String
add_name_to_mail m n = n ++ " <" ++ m ++ ">"


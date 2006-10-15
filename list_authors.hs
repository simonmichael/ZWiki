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
-- along with this program; if not, write to the Free Software Foundation,
-- Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

module Main (main) where

import DarcsUtils ( formatPath )
import DarcsRepo ( read_repo )
import PatchInfo ( pi_author )

import Data.List ( sort, group )
import System ( getProgName, getArgs )
import Monad ( liftM )

intro :: Bool -> IO String
intro do_stats = do
  prog_name <- getProgName
  return $
    "This is a list of ALL contributors to this repo, sorted according to the\n"++
    "number of patches they have contributed.  This list is automatically\n"++
    "created from the darcs repository, so if there are problems with it,\n"++
    "changes should be made to list_authors.hs.\n"++
    "\n" ++
    (if do_stats
     then ""
     else ("Run " ++ formatPath (prog_name ++ " stats") ++
           " for more detailed information.\n" ++ "\n"))

main :: IO ()
main = do darcs_history <- read_repo "."
          use_statistics <- elem "stats" `liftM` getArgs
          intro use_statistics >>= putStr
          mapM_ putStrLn $ sort_authors use_statistics $ map (pi_author.fst)
                         $ concat darcs_history

-- contributors who only provided an email address, one for which we know the name
-- note that having an entry in this table counts as two addresses... so if there 
-- another address used besides this entry, you should remove it from the table,
-- add a constant (above) and modify canonize_authors (below)
-- XXX check this & clean up
authors_sans_name :: [ (String, String) ]
authors_sans_name =
  [ 
    ("encolpe.degoute@ingeniweb.com"   , "Encolpe Degoute"),
    ("simon@joyful.com"                , "Simon Michael"),
    ("bob+zwiki@mcelrath.org"          , "Bob McElrath"),
    ("lele@seldati.it"                 , "Lele Gaifax"),
    ("nachtigall@web.de"               , "Jens Nachtigall"),
    ("frank@laurijssens.nl"            , "Frank Laurijssens"),
    ("foenyx@online.fr"                , "Nicolas Laurent"),
    ("stefan.rank@oefai.at"            , "Stefan Rank"),
    ("tcchou@tcchou.org"               , "T. C. Chou"),
    ("stefan.rank@ofai.at"             , "Stefan Rank"),
    ("bill.page1@sympatico.ca"         , "Bill Page"),
    ("riley@uic.com"                   , "John Riley"),
    ("jbb@contradix.com"               , "Jordan Baker"),
    ("alvaro@antalia.com"              , "Alvaro Cantero"),
--    ("klippe@pf.pl"                    , ""),
--    ("huron@sopinspace.com"            , ""),
--    ("an.ma@web.de"                    , ""),
    ("","")
  ]

canonize_author :: String -> String
canonize_author s
    | s `contains` "simon@blue"        = "Simon Michael <simon@joyful.com>"
    | s `contains` "simon@dynabook.joyful.com"        = "Simon Michael <simon@joyful.com>"
    | s `contains` "sendencolpe.degoute" = "Encolpe Degoute <encolpe.degoute@ingeniweb.com>"
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


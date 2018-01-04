#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import copy
import xml.etree.ElementTree as ET


# Pro snadnější čitelnost kódu:
BIT = 1
INT = 2
FLOAT = 3
STR = 4
NVARCHAR = 5
NTEXT = 6


def print_err(text, number):
    """tiskne error na vystup stderr + ukonci program s urcenou hodnotou (dle zadani)"""

    output = "ERROR:" + text + "\n"
    sys.stderr.write(output)
    sys.exit(number)

# inspirace pouziti parse_args()
# z manuálových stránek: https://docs.python.org/2/howto/argparse.html
# funkce parsovani parametru
# volana pro nacteni parametru programu (na zacatku programu)
# vraci strukturu naplnenou parametry
# tato funkce nekontroluje porušení kombinací parametrů o to se stará param_check()
def param_parse():
    """funkce pro parsovani parametru"""
    hphrases = [
        "vypise napovedu na standartni vystup",

        "zadany vstupni soubor ve formatu XML",

        "zadany vystupni soubor ve formatu definovanam vyse",

        "na zacatek vystupniho souboru se vlozi zakomentovana hlavicka",

        "pouziti: (--etc=n) pro n ≥ 0 urcuje maximalni pocet"
        "sloupcu vzniklych ze stejnojmennych podelementu",

        "nebudou se generovat sloupce z atributu ve vstupním XML souboru",

        "pokud bude element obsahovat vice podelementů stejneho nazvu,"
        "bude se uvazovat, jako by zde byl pouze jediny takovy (tento parametr"
        "nesmi byt kombinovan s parametrem --etc=n)",

        "lze jej uplatnit v kombinaci s jakymikoliv jinymi prepinaci"
        "vyjma --help. Pri jeho aktivaci bude vastupnim souborem pouze XML"
        "definovaneho tvaru v zadani",

        "obsahuje data, ktera lze bezezbytku vlozit do databazove struktury"
        "tabulek vznikle pro soubor dany parametrem"
    ]

    params = argparse.ArgumentParser(add_help=False)
    params.add_argument("-h", "--help", action="count", default=0, help=hphrases[0])
    params.add_argument("--input", action="append", default=[], help=hphrases[1])
    params.add_argument("--output", action="append", default=[], help=hphrases[2])
    params.add_argument("--header", action="append", default=[], help=hphrases[3])
    params.add_argument("--etc", action="append", default=[], help=hphrases[4])
    params.add_argument("-a", action="count", default=0, help=hphrases[5])
    params.add_argument("-b", action="count", default=0, help=hphrases[6])
    params.add_argument("-g", action="count", default=0, help=hphrases[7])
    params.add_argument('--isvalid', action="append", default=[], help=hphrases[8])
    return params

# prvne vola paramsParse pro nacteni argumentu, -> ulozi si je do promnene args
# vraci overene parametry programu
def param_check():
    """vraci overene parametry programu"""

    try:
        args = param_parse().parse_args()
    except:
        print_err("Spatne zadane paramtery, pro radu pouzite prepinac --help", 1)

    if (args.help == 1) and (len(sys.argv) == 2):
        param_parse().print_help()
        sys.exit(0)
    elif args.help > 0:
        print_err("Nepovolena kombinace argumetnu: help + dalsi argument", 1)

    if len(args.input) > 1:
        print_err("Je mozny pouze jeden vstupni soubor", 1)

    if len(args.output) > 1:
        print_err("Je mozny pouze jeden vystupni soubor", 1)

    if len(args.header) > 1:
        print_err("Je mozny pouze jedna hlavicka vystupniho souboru", 1)

    if len(args.etc) > 1:
        print_err("Je mozny pouze jednou zadane etc", 1)

    if len(args.isvalid) > 1:
        print_err("Je mozne zadat pouze jeden soubor na validovani", 1)

    if args.a > 1:
        print_err("chyba v prepinaci -a, pro radu spustte program s predvolbou --help, nebo -h", 1)

    etc_lenght = len(args.etc)
    if args.b > 1 or (args.b > 0 and  etc_lenght > 0):
        print_err("chyba v prepinaci -b, pro radu spustte program s predvolbou --help, nebo -h", 1)

    if args.g > 1:
        print_err("chyba v prepinaci -a, pro radu spustte program s predvolbou --help, nebo -h", 1)

    return args

# Třída pro elementy stromu, obsahuje 3 atributy:
#   - tag       = je roven názvu tabulky, slouží pro snadnější
#                 implementaci ostatních třídních metod
#   - atributs  = obsahuje slovník atributů danné tabulky, u každého atributu
#                 uchovává informace o jméně atributu (ve formě klíče) a typu
#   - fkey        = uchovává všechny cizý klíče danné tabulky, v případě, že se
#                 stejně tak i jeho četnost v rámci tabulky
class TableElement:
    """trida pro abstrakne definujici vyslednou tabulky a jeji prvky"""
    def __init__(self, tag):
        self.tag = tag
        self.atributs = {}
        self.fkey = {}

    # pomocny vypis pri debuggovani
    def __repr__(self):
        string = "\n--------------------\n"
        string += "Prvek: {}\n".format(self.tag)
        string += "Atributs: {} \n".format(self.atributs)
        string += "fkeyeyS: {}\n".format(self.fkey)
        string += "--------------------\n"
        return string

    def give_atr(self, name, type_of_elm):
        """prida atribut zvolene tabulce"""
        try:
            if self.atributs[name] < type_of_elm:
                self.atributs[name] = type_of_elm
        except:
            self.atributs[name] = type_of_elm


    def givefkey(self, tag, count):
        """prida cizy klic daneme tabulce"""
        if tag not in self.fkey:
            self.fkey[tag] = count
        else:
            if self.fkey[tag] < count:
                self.fkey[tag] = count

    def removefkey(self, tag):
        """odsrani cizy klic z dane tabulky"""
        del self.fkey[tag]

# funkce gettype_of_elm(element) vrací řetězec - typ elementu podle zadání
def get_type(element):
    """vraci typ predaneho elementu"""

    # test zda-li se jedná o bitovou hodnotu
    if element == '1' or element == '0' or element == 'false' or element == 'true':
        return BIT

    # test zda-li se jedná o celé číslo
    try:
        int(element)
        return INT
    except ValueError:
        pass

    # test zda-li se jedná o číslo s plovoucím desetiným místem
    try:
        float(element)
        return FLOAT
    except ValueError:
        pass

    # jinak se jedná o řetězec
    # poslední kontrola jestli se nejedná o prázdný řetězec
    # (myšleno, že je sestaven pouze bílými znaky)
    if element.strip() == "":
        return BIT
    return STR

# rekurzí implemenotvaná funkce jež slouží pro průchod stromem který byl
# vytvořen pomocí ET.parse().
# nemá návratovou hodnotu, jejím výsledkem je sestavená hierarchie tabulek,
# atributů a cizých klíčů v zadaeném slovníku.
# informace o existenci parametru '-a' je předávána pomocí promněnné 'param_a'
# v případě, že je přítomna, negenerují se sloupce z atributů.
def do_xml(tree, root, param_a, work_dict):
    """funcke analyzuje predanou stromovou strukturu a inicializuje jednotlive tabulky"""

    # pomocný set cizých klíčů, po projití uzlem uložen do atributu 'fkey'
    # Elementu daného uzlu
    counter = {}

    # zpracovani vsech potomku root korene, do hloubky.
    # implementovano rekurzi
    # vytvoreni seznamu Atributu daného Tagu v tabulce TableElementů
    for child in root.getchildren():
        child.tag = child.tag.lower()
        if child.tag not in work_dict.keys():
            work_dict[child.tag.lower()] = TableElement(child.tag.lower())

        if root != tree.getroot():
            try:
                counter[child.tag] += 1
            except:
                counter[child.tag] = 1

        if not param_a:
            for actual in child.attrib:
                tag = child.tag.lower()
                if get_type(child.attrib[actual].lower()) == STR:
                    work_dict[tag].give_atr(actual.lower(), NVARCHAR)
                else:
                    attr = child.attrib
                    work_dict[tag].give_atr(actual.lower(), get_type(attr[actual.lower()].lower()))
        do_xml(tree, child, param_a, work_dict)

    # zpracovani textu v aktualnim Elementu
    if format(root.text).strip() != '' and root.text != None:
        data = get_type(root.text.lower())
        if data == STR:
            data = NTEXT

        # osetření případů kdy daný atribut již existuje, v tom případě se
        # kontroluje jeho hodnota a v případě že je nižší než aktuální, tak se
        # přepíše
        try:
            value = work_dict[root.tag.lower()].atributs["value"]
            if data > value:
                work_dict[root.tag.lower()].atributs["value"] = data
        except:
            work_dict[root.tag.lower()].atributs["value"] = data


    for key in counter:
        key = key.lower()
        work_dict[root.tag.lower()].givefkey(key, counter[key])

# funkce jež tiskne na zvolený výstup (stdout, nebo zadaný soubor)
# v předepsané formě, která je otpovídá DDL
def print_ddl(ostream, args, namespace, work_dict):
    """tiskne vyslednou podobu prikazu pro vytvoreni pozadovanych tabulek"""

    # pokud je uživatelem zadána hlavička, je tisknuta
    # přednostně na počátek výstupu
    if len(args.header) == 1:
        output = "--"
        output += args.header[0]
        output += "\n\n"
        ostream.write(output)

    # pro každou reprezentaci tabulky v setu work_dict se prvně
    # vytvoří danná tabulka, automaticky se z jejího názvu vygeneruje její
    # primární klíč, následně se doplní její cizý klíče a nakonec její atributy
    for table in work_dict:
        output = "CREATE TABLE "

        # odstranení namespace
        if table.startswith(namespace):
            table = table[len(namespace):]
        output += table
        output += "(\n  prk_"
        output += table
        output += "_id INT PRIMARY KEY"
        ostream.write(output)

        for fkey in work_dict[namespace + table].fkey:
            output = ",\n  "

            # odstranení namespace
            if fkey.startswith(namespace):
                fkey = fkey[len(namespace):]
            output += fkey
            output += "_id INT"
            ostream.write(output)

        for atribut in work_dict[namespace + table].atributs:
            typ = work_dict[namespace + table].atributs[atribut]
            output = ",\n  "

            # odstranení namespace
            if atribut.startswith(namespace):
                atribut = atribut[len(namespace):]
            output += atribut
            output += " "
            if typ == 1:
                output += "BIT"
            elif typ == 2:
                output += "INT"
            elif typ == 3:
                output += "FLOAT"
            elif typ == 4:
                output += "STR"
            elif typ == 5:
                output += "NVARCHAR"
            elif typ == 6:
                output += "NTEXT"
            ostream.write(output)

        ostream.write("\n);\n\n")

# pomocna funkce pro modelaci transitivniho vztahu A -> B pro A -> C -> B
# parametry jsou:
# 1. ) tabulka tabulek relací
# 2. ) pomocná tabulka tabulek relací (nelze přímo zapisovat do rel,
#      z důvodu změny ve for-cyklu)
# 3. ) "A"
# 4. ) "B"
# 5. ) "C" - přemostění těchto tabulek, jako jediná obsahuje relace jak s A
#            tak i s B
def get_rel(rel, helper, rel_a, rel_b, over):
    """uklada hodnotu kardinalit relace"""

    helper[rel_a][rel_b] = {}
    helper[rel_a][rel_b]["vlastni"] = rel[rel_a][over]["vlastni"]
    helper[rel_a][rel_b]["cizy"] = rel[over][rel_b]["cizy"]

# funkce kontroluje transitivitu relací
# v případě, že se během jedné kontroly generuje alespoň jedna nová,
# je třeba tuto funky zavolat znovu z důvodů opětovné kontroly
def transit(rel, helper):
    changed = False
    for table in rel:
        for relation in rel[table]:
            for far in rel[relation]:
                if rel[relation][far]["vlastni"] == "1":
                    if rel[relation][far]["cizy"] == "1":
                        rel[relation][far]["vlastni"] = "N"
                        rel[relation][far]["cizy"] = "N"

    # for-cyklus pro nalezeni možných vazeb
    for over in rel:
        for rel_a in rel[over]:
            for rel_b in rel[over]:
                if rel_b != rel_a:
                    get_rel(rel, helper, rel_a, rel_b, over)

    # aplikace najitých vazeb do rel z helper, v případě že byla alepoň jedna
    # najita je funkce transit() volaná znovu, pro opětovnou kontrolu
    for table in helper:
        for relation in helper[table]:
            if relation not in rel[table]:
                rel[table][relation] = helper[table][relation]
                changed = True
        helper[table] = {}


    if changed:
        transit(rel, helper)

# funkce ktera vypíše do zvoleného výstupu, relace jednotlivých elementů databáze
# a následně poté se program ukončí (netisknou se příkazy pro sestavení databází)
def print_g(ostream, args, namespace, work_dict):
    rel = {}
    helper = {}

    # inicializace rel seznamu + u kazde tabulky vedeni relace na sebe sama
    for table in work_dict:
        helper[table] = {}
        rel[table] = {}
        rel[table][table] = {
            "vlastni": "1",
            "cizy" : "1"
        }
    for table in work_dict:
        table = table.lower()
        for key in work_dict[table].fkey:
            key = key.lower()

            # ošetření cyklu A odkazuje do B (N:1)
            #                B odkazuje do A (N:1) nebo naopak.
            if key in rel[table]:
                rel[table][key] = {
                    "vlastni": "N",
                    "cizy" : "N"
                }
                rel[key][table] = {
                    "vlastni": "N",
                    "cizy" : "N"
                }
            else:
                rel[table][key] = {
                    "vlastni": "1",
                    "cizy" : "N"
                }
                rel[key][table] = {
                    "vlastni": "N",
                    "cizy" : "1"
                }

    transit(rel, helper)

    # ------------- VYPIS G-VAZEB ------------------------#

    # pokud je uživatelem zadána hlavička, je tisknuta
    # přednostně na počátek výstupu
    if len(args.header) == 1:
        output = "--"
        output += args.header[0]
        output += "\n\n"
        ostream.write(output)

    output = '<?xml version="1.0" encoding="UTF-8"?>\n'
    output += "<tables>\n"
    for table in rel:
        output += "    <table name=\""
        # ---- odstraneni namespace
        if table.startswith(namespace):
            table = table[len(namespace):]
        output += table
        output += "\">\n"
        # ++++ pridani namespace pro další iterace
        table = namespace + table

        for key in rel[table]:
            output += "        <relation to=\""
            # ---- odstranení namespace
            if key.startswith(namespace):
                key = key[len(namespace):]
            output += key
            output += "\" relation_type=\""
            # ++++ pridani namespace pro další iterace
            key = namespace + key
            if (rel[table][key]["cizy"] == rel[table][key]["vlastni"]) and (key != table):
                output += "N:M"
            elif key == table:
                output += "1:1"
            else:
                output += rel[table][key]["cizy"]
                output += ":"
                output += rel[table][key]["vlastni"]
            output += "\" />\n"
        output += "    </table>\n"

    output += "</tables>\n"
    ostream.write(output)

# Funkce volaná pokud není zadán parametr '-b', kontroluje počty výskytů cizých
# klíčů v jednotlivých tabulkách, pokud je tento počet vyšší jak
# jedna, přejmenuje všechny výskyty a přiřadí na konec jejich původního jména
# identifikátor (1 ... n), kde n je počet výskytů daného cizýho klíče v dané
# tabulce.
# Výjimka: v případě že v tabulce již existuje klíč ve tvaru "nazevn" je zvolené
# n posunuto o jedna, dokud tato podmínka není porušena
def name_check(work_dict):
    """funcke pro kontrolu poctu vyskytu stejnojmennych elementu"""

    # zaloha
    old = copy.deepcopy(work_dict)

    for table in work_dict:
        del_key = []
        local_elem = TableElement(table)
        for key in work_dict[table].fkey:
            if work_dict[table].fkey[key] > 1:
                count = work_dict[table].fkey[key]
                i = 1
                while i < (count + 1):
                    if key + str(i) in work_dict[table].fkey:
                        count += 1
                    else:
                        tag = key + str(i)
                        local_elem.givefkey(tag, INT)
                    i += 1
                del_key.append(key)
            else:
                local_elem.givefkey(key, work_dict[table].fkey[key])

        if local_elem.fkey != {}:
            for key in local_elem.fkey:
                work_dict[table].givefkey(key, local_elem.fkey[key])
            for key in del_key:
                work_dict[table].removefkey(key)
    return old

# Funkce pro rozšíření: VAL, parametry příjmá: string obsahující umístění souboru
# a parametry programu v promněnné args, při úspěsné validaci nic nevrací,
# pří chybě při validaci ukončí program s chybovou hláškou a 91
def valid_check(to_valid, args, old_table, work_dict, val_dict):
    """funkce pro validaci, bez navratove hodnoty, ukoncuje program v pripade chyby"""

    try:
        valdata = open(to_valid, "r")
    except:
        print_err("Nepovedlo se otevrit zvoleny soubor", 2)

    try:
        tree = ET.parse(valdata)  # parse an open file
        root = tree.getroot()
    except:
        print_err("Vstupni soubor pro validaci neni validni XML soubor", 4)

    do_xml(tree, root, args.a, val_dict)

    # B - parametr
    # ošetření případu, kdy je v jedné tabulce více stejnojmenných klíčů
    # v případě, že je zadán parametr '-b', se tato oprava neprovádí
    # a program se chová jakoby byl zadán pouze jediný takový
    # informace o upravenych jmenech ulozena do promnených deleted
    if not args.b:
        old_val_table = name_check(val_dict)

    # Tělo validace -
    # Hierarchie tabulek je uložena v globalní promněnné val_dict

    for val in work_dict:

        # kontrola zda-li extují stejné tabulky
        if val not in work_dict:
            err_text = "Některý název zabulky ze souboru"
            err_text += " pro validaci nelze vložit do vysledne hierarchie"
            print_err(err_text, 91)

        # kontrola zda-li v daných tabulkách existují stejné cizý klíče
        try:
            for fkey in val_dict[val].fkey:
                if fkey not in work_dict[val].fkey:
                    err_text = "Cizý klíč tabulky ze souboru"
                    err_text += " pro validaci nelze vlozit do tabulky zadane vstupnim souborem "
                    print_err(err_text, 91)
        except KeyError:
            print_err("Tabulky vlozene souborem pro validaci nejsou shodne s tabulkami definovanymi vstupnim souborem", 91)


        # kontrola zdali u daných tabulek jsou shodné atributy, následně zda-li
        # odpovídají i datové typy atributů - atribut s nižším datovým typem
        # může být vložen do atributu s vyšším typem, tato operace ovšem není
        #
        try:
            for atr in val_dict[val].atributs:
                if atr not in work_dict[val].atributs:
                    err_text = "Atribut ze zadanáho souboru"
                    err_text += " pro validaci se neshoduje s atributy výsledných tabulek "
                    print_err(err_text, 91)

                if val_dict[val].atributs[atr] > work_dict[val].atributs[atr]:
                    err_text = "Atribut ze zadaného souboru"
                    err_text += " pro validaci má vyšší datový typ než je stanoven základním souborem"
                    print_err(err_text, 91)
        except KeyError:
            print_err("Atributy vlozene souborem pro validaci nejsou shodne s atributy tabulek definovanymi vstupnim souborem", 91)


    # upraveni nazvu po kontrole zpět do tvaru nazevN bez N na konci pokud je
    # zadán argument -g

    if not args.b and args.g:
        work_dict = old_table
        val_dict = old_val_table

# Funkce pro kontrolu kolize jmenprimárních a cizých klíčů.
# Případně jmen primárních klíčů, nebo cizých klíčů a atributů
def inspect(work_dict):
    """funkce pro kontrolu moznych kolizi klicu a atrtibutu"""

    for table in work_dict:
        for key in work_dict[table].fkey:

            # Ošetření případu kdy se primární klíč tabulky shoduje s cizým
            # klíčem tabulky

            if "pkr_" + table + "_id" == key + "_id":
                print_err("Konflikt jména primárního a cizýho klíče tabulky", 90)

            # Kontrola Atributů tabulky, zda-li nekolidují s primárními a
            # cizými klíči tabulek

            for atribut in work_dict[table].atributs:
                if key + "_id" == atribut:
                    print_err("Konflikt jména atributu a cizýho klíče tabulky", 90)
                if "pkr_" + table + "_id" == atribut:
                    print_err("Konflikt jména atributu a primárního klíče tabulky", 90)

# Řídící tělo programu
# 1. )  analýza parametrů programu + ošetření vstupního a výstupního souboru,
#       v případě že byl zadán
# 2. )  v případě validního vstupního XML souboru následně probíhá zpracování
#       vstupu
# 3. )  ošetření maximálního počtu sloupců vzniklých ze stejného jména (--etc)
# 4. )
#
#
#
# ----- TELO PROGRAMU --------- #

def main():
    # Slovníky, používané téměř každou funkcí, proto jsou často jejich ukazatele
    # předávány do parametrů funkcí, druhou možnou implementací, by bylo je
    # uvést globálně

    work_dict = {}
    val_dict = {}

    args = param_check()
    istream = sys.stdin
    ostream = sys.stdout

    # ---- OSETRENI PRI ZADANEM VSTUPNIM SOUBORU ---- #
    if len(args.input) == 1:
        try:
            istream = open(args.input[0], "r")
        except:
            print_err("Nepovedlo se otevrit zvoleny soubor", 2)

    # ---- OSETRENI PRI ZADANEM VYSTUPNIM SOUBORU ---- #
    if len(args.output) == 1:
        try:
            ostream = open(args.output[0], "w")
        except:
            print_err("Nepovedlo se otevrit zvoleny soubor", 3)

    # ------------ ZPRACOVÁNÍ VSTUPU ------------#
    # implementováno pomocí xml.elementtree
    # inpirace https://docs.python.org/3.4/library/xml.etree.elementtree.html
    try:
        tree = ET.parse(istream)  # parse an open file
        root = tree.getroot()
    except:
        print_err("Vstupni soubor neni validni XML soubor", 4)

    # získání jmenného prostoru
    if root.tag[0] == "{":
        namespace = root.tag[root.tag.find("{")+1:root.tag.find("}")]
        namespace = "{" + namespace + "}"
    else:
        namespace = ""

    # strom se analyzuje pomocí funkce do_xml()
    do_xml(tree, root, args.a, work_dict)

    # ETC - parametr
    # vysetreni parametru --etc = n, tento parametr nesmí být zadán společně s
    # '-b', udává maximlní počet sloupců vzniklých ze stejnojmenných podelemntů
    # v případě, že počet stejnojmenných odkazů je vyší než zadané n, je daná
    # vazba obrácena, a informace uložena do cizýho klíče tabulky na "opačné
    # straně vazby"

    if args.etc != []:
        try:
            num = int(args.etc[0])
        except:
            print_err("chyba v parametru --etc", 1)

        for table in work_dict:
            table = table.lower()
            to_del = []
            for key in work_dict[table].fkey:
                key = key.lower()
                count = work_dict[table].fkey[key]
                if count > int(num):
                    if table in work_dict[key].fkey:
                        print_err("Konflikt jmen cizých klíčů při konverzi tabulek", 90)
                    work_dict[key].givefkey(table, 0)
                    to_del.extend([key])
            for i in to_del:
                i = i.lower()
                del work_dict[table].fkey[i]


    # B - parametr
    # ošetření případu, kdy je v jedné tabulce více stejnojmenných klíčů
    # v případě, že je zadán parametr '-b', se tato oprava neprovádí
    # a program se chová jakoby byl zadán pouze jediný takový

    old_table = None
    if not args.b:
        old_table = name_check(work_dict)
    # ošetření konfliktu názvu sloupců vznikajících z atributů
    # nebo textového obsahu

    inspect(work_dict)

    # G - parametr
    # výstupem v tomto případě je XML soubor popu
    if args.g:
        if args.isvalid != []:
            valid_check(args.isvalid[0], args, old_table, work_dict, val_dict)
            if not args.b:
                work_dict = old_table
            print_g(ostream, args, namespace, work_dict)

            if len(args.output) == 1:
                ostream.close()
            if len(args.input) == 1:
                istream.close()
            sys.exit(0)
        else:
            inspect(work_dict)
            if not args.b:
                work_dict = old_table
            print_g(ostream, args, namespace, work_dict)

            if len(args.output) == 1:
                ostream.close()
            if len(args.input) == 1:
                istream.close()
            sys.exit(0)


    # Implementace rozšíření VAL

    if args.isvalid != []:
        valid_check(args.isvalid[0], args, old_table, work_dict, val_dict)


    # volání funkce pro tisk výsledku do zadaného výstupního souboru = 'ostream'
    print_ddl(ostream, args, namespace, work_dict)

    if len(args.output) == 1:
        ostream.close()
    if len(args.input) == 1:
        istream.close()
    sys.exit(0)


if __name__ == "__main__":
    main()

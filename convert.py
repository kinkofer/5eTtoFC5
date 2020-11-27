# vim: set tabstop=8 softtabstop=0 expandtab shiftwidth=4 smarttab : #
import xml.etree.cElementTree as ET
import json
import re
import sys
import os
import argparse
import copy
import requests
import tempfile
import shutil

import utils
from monster import parseMonster
from item import parseItem
from spell import parseSpell
from cclass import parseClass
from background import parseBackground
from feat import parseFeat
from race import parseRace
from featureAsFeat import parseFeature

# Argument Parser
parser = argparse.ArgumentParser(
    description="Converts 5eTools json files to FC5 compatible XML files.")
parser.add_argument('inputJSON', nargs="*", type=str, help="5eTools inputs")
parser.add_argument(
    '--ignore',
    dest="IE",
    action='store_const',
    const=True,
    default=False,
    help="ignores errors (default: false)")
parser.add_argument(
    '-v',
    dest="verbose",
    action='store_const',
    const=True,
    default=False,
    help="verbose output (default: false)")
parser.add_argument(
    '-o',
    dest="combinedoutput",
    action='store',
    default=False,
    help="combines inputs into given output (default: false)")
parser.add_argument(
    '--show-dupes',
    dest="showdupe",
    action='store_const',
    const=True,
    default=False,
    help="show duplicates (default: false)")
parser.add_argument(
    '--no-html',
    dest="nohtml",
    action='store_const',
    const=True,
    default=False,
    help="no html tags (default: false)")
parser.add_argument(
    '--images',
    dest="addimgs",
    action='store_const',
    const=True,
    default=False,
    help="copy images to compendium directories (default: false)")
parser.add_argument(
    '--futuristic-items',
    dest="futuristic",
    action='store_const',
    const=True,
    default=False,
    help="include futuristic items (default: false)")
parser.add_argument(
    '--modern-items',
    dest="modern",
    action='store_const',
    const=True,
    default=False,
    help="include modern items (default: false)")
parser.add_argument(
    '--renaissance-items',
    dest="renaissance",
    action='store_const',
    const=True,
    default=False,
    help="include renaissance items (default: false)")
parser.add_argument(
    '--update-data-from',
    dest="updatedata",
    action='store',
    default=None,
    nargs=1,
    help="update date from url")
parser.add_argument(
    '--skip-ua',
    dest="skipua",
    action='store_const',
    default=False,
    const=True,
    help="skip UA content")
parser.add_argument(
    '--srd',
    dest="srd",
    action='store_const',
    default=False,
    const=True,
    help="only SRD content")
officialsources = [
    # "PHB",
    # "MM",
    # "DMG",
    # "SCAG",
    # "VGM",
    # "XGE",
    # "MTF",
    # "GGR",
    # "AI"
    # "ERLW",
    # "RMR",
    # "LMoP",
    # "HotDQ",
    # "RoT",
    # "PotA",
    # "OotA",
    # "CoS",
    # "SKT",
    # "TftYP",
    # "ToA",
    # "TTP",
    # "WDH",
    # "WDMM",
    # "KKW",
    # "LLK",
    # "GoS",
    # "OoW",
    # "DIP",
    # "HftT",
    # "DC",
    # "SLW",
    # "SDW",
    # "BGDIA",
    # "RMBRE",
    # "SADS",
    # "MFF",
    # "ESK",
    # "EGW",
    # "MOT",
    # "TCE",
    # "AWM",
    # "IMR",
    # "OGA",
    # "LR",
    # "DD",
    # "ALRageOfDemons",
    # "ALElementalEvil",
    # "ALCurseOfStrahd",
    # "PSA",
    # "PSD"
    # "PSI",
    # "PSK",
    # "PSX",
    # "PSZ",
    # "EET",
    # "EEPC",
    # "RoTOS",
    # "UAWGE",
    # "UAPrestigeClassesRunMagic",
    # "UAModernMagic",
    # "UA2020SpellsAndMagicTattoos",
    # "UAFeats",
    # "UA2020PsionicOptionsRevisited",
    # "UAFeatsForRaces",
    # "UAEberron",
    # "UAFeatsForSkills",
    # "UA2020Feats",
    # "UAFighterRogueWizard",
    # "UAWaterborneAdventures",
    # "UAGothicHeroes",
    # "UARacesOfEberron",
    # "UAEladrinAndGith",
    # "UACentaursMinotaurs",
    # "UARacesOfRavnica",
    # "UAOfShipsAndSea",
    # "UAArtificerRevisited",
    # "UAArtificer",
    # "UARevisedSubclasses",
    # "UA2020SubclassesPt1",
    # "UABarbarianPrimalPaths",
    # "UABarbarianAndMonk",
    ]
officialsources = utils.getPublishedSources()
parser.add_argument(
    '--only-official',
    dest="onlyofficial",
    action='store_const',
    default=None,
    const=officialsources,
    help="only include officially released content from: " + ", ".join([utils.getFriendlySource(x) for x in officialsources]) )
parser.add_argument(
    '--onlysrc',
    dest="onlysrc",
    action='store',
    default=None,
    nargs=1,
    help="Limit to specific source")
parser.add_argument(
    '--temp-dir',
    dest="tempdir",
    action='store',
    default=None,
    help="directory to use for temporary files when generating Encounter+ compendium" )
args = parser.parse_args()
tempdir = None
if args.onlysrc:
    args.onlyofficial = args.onlysrc
    args.allowedsrc = officialsources+args.onlysrc
else:
    args.allowedsrc = args.onlyofficial
if args.combinedoutput and args.combinedoutput.endswith(".compendium"):
    if not args.tempdir:
        tempdir = tempfile.TemporaryDirectory(prefix="5eToE_")
        args.tempdir = tempdir.name
if not args.tempdir:
    args.tempdir = "."
if args.updatedata:
    if not args.updatedata[0].startswith("http"):
        baseurl = "https://{}/data".format(args.updatedata[0].rstrip('/'))
    else:
        baseurl = "{}/data".format(args.updatedata[0].rstrip('/'))
    datadir = "data"
    classdir = os.path.join(datadir,"class")
    bestiarydir = os.path.join(datadir,"bestiary")
    spellsdir = os.path.join(datadir,"spells")
    items = [ 'items.json','items-base.json','magicvariants.json','vehicles.json','fluff-vehicles.json','backgrounds.json','fluff-backgrounds.json','feats.json','races.json','fluff-races.json','books.json','adventures.json','optionalfeatures.json' ]

    try:
        if not os.path.exists(datadir):
            os.mkdir(datadir)
        if not os.path.exists(classdir):
            os.mkdir(classdir)
        if not os.path.exists(bestiarydir):
            os.mkdir(bestiarydir)
        if not os.path.exists(spellsdir):
            os.mkdir(spellsdir)

        for f in items:
            print("Downloading:","/"+f)
            req = requests.get(baseurl + "/"+f)
            with open(os.path.join(datadir,f), 'wb') as f:
                f.write(req.content)
                f.close()
        print("Downloading bestiary index:","/bestiary/index.json")
        req = requests.get(baseurl + "/bestiary/index.json")
        with open(os.path.join(bestiarydir,"index.json"), 'wb') as f:
            f.write(req.content)
            f.close()
        with open(os.path.join(bestiarydir,"index.json"),encoding='utf-8') as f:
            idx = json.load(f)
            f.close()
        for k,v in idx.items():
            print("Downloading source {}: {}".format(k,v))
            req = requests.get(baseurl + "/bestiary/" + v)
            with open(os.path.join(bestiarydir,v), 'wb') as f:
                f.write(req.content)
                f.close()
        print("Downloading bestiary fluff index:","/bestiary/fluff-index.json")
        req = requests.get(baseurl + "/bestiary/fluff-index.json")
        with open(os.path.join(bestiarydir,"fluff-index.json"), 'wb') as f:
            f.write(req.content)
            f.close()
        with open(os.path.join(bestiarydir,"fluff-index.json"),encoding='utf-8') as f:
            idx = json.load(f)
            f.close()
        for k,v in idx.items():
            print("Downloading fluff source {}: {}".format(k,v))
            req = requests.get(baseurl + "/bestiary/" + v)
            with open(os.path.join(bestiarydir,v), 'wb') as f:
                f.write(req.content)
                f.close()
        req = requests.get(baseurl + "/bestiary/legendarygroups.json")
        with open(os.path.join(bestiarydir,"legendarygroups.json"), 'wb') as f:
            f.write(req.content)
            f.close()
        print("Downloading class index:","/class/index.json")
        req = requests.get(baseurl + "/class/index.json")
        with open(os.path.join(classdir,"index.json"), 'wb') as f:
            f.write(req.content)
            f.close()
        with open(os.path.join(classdir,"index.json"),encoding='utf-8') as f:
            idx = json.load(f)
            f.close()
        for k,v in idx.items():
            print("Downloading source {}: {}".format(k,v))
            req = requests.get(baseurl + "/class/" + v)
            with open(os.path.join(classdir,v), 'wb') as f:
                f.write(req.content)
                f.close()
        print("Downloading spells index:","/spells/index.json")
        req = requests.get(baseurl + "/spells/index.json")
        with open(os.path.join(spellsdir,"index.json"), 'wb') as f:
            f.write(req.content)
            f.close()
        with open(os.path.join(spellsdir,"index.json"),encoding='utf-8') as f:
            idx = json.load(f)
            f.close()
        for k,v in idx.items():
            print("Downloading source {}: {}".format(k,v))
            req = requests.get(baseurl + "/spells/" + v)
            with open(os.path.join(spellsdir,v), 'wb') as f:
                f.write(req.content)
                f.close()
    except Exception as e:
        print("Could not update data:",e)
    sys.exit()

excludedages = []
if not args.futuristic:
    excludedages.append('futuristic')
if not args.modern:
    excludedages.append('modern')
if not args.renaissance:
    excludedages.append('renaissance')

if args.combinedoutput:
    # Building XML file
    compendium = ET.Element(
        'compendium', {'version': "5", 'auto_indent': "NO"})
    mwins = 0
    mloss = 0
    mdupe = 0
    iwins = 0
    iloss = 0
    idupe = 0
    swins = 0
    sloss = 0
    sdupe = 0
    bwins = 0
    bloss = 0
    bdupe = 0
    fwins = 0
    floss = 0
    fdupe = 0
    rwins = 0
    rloss = 0
    rdupe = 0
    cwins = 0
    closs = 0
    cdupe = 0
    afdupe = 0
    afwins = 0
    afloss = 0
    aidupe = 0
    aiwins = 0
    ailoss = 0
    asdupe = 0
    aswins = 0
    asloss = 0
    eddupe = 0
    edwins = 0
    edloss = 0
    eidupe = 0
    eiwins = 0
    eiloss = 0
    mvdupe = 0
    mvwins = 0
    mvloss = 0
    ordupe = 0
    orwins = 0
    orloss = 0
    pbdupe = 0
    pbwins = 0
    pbloss = 0
    rndupe = 0
    rnwins = 0
    rnloss = 0
for file in args.inputJSON:
    with open(file,encoding='utf-8') as f:
        d = json.load(f)
        f.close()
    fluff = None
    if '_meta' in d:
        args.filemeta = d['_meta']
    else:
        args.filemeta = None
    if os.path.isfile(os.path.split(file)[0] + "/fluff-" + os.path.split(file)[1]):
        if args.verbose:
            print("Fluff file found:",os.path.split(file)[0] + "/fluff-" + os.path.split(file)[1])
        with open(os.path.split(file)[0] + "/fluff-" + os.path.split(file)[1],encoding='utf-8') as f:
            fluff = json.load(f)
            f.close()

    ignoreError = args.IE
    if not args.combinedoutput:
        # Building XML file
        compendium = ET.Element(
            'compendium', {
                'version': "5", 'auto_indent': "NO"})
        mwins = 0
        mloss = 0
        mdupe = 0
        iwins = 0
        iloss = 0
        idupe = 0
        swins = 0
        sloss = 0
        sdupe = 0
        bwins = 0
        bloss = 0
        bdupe = 0
        fwins = 0
        floss = 0
        fdupe = 0
        rwins = 0
        rloss = 0
        rdupe = 0
        rwins = 0
        rloss = 0
        rdupe = 0
        rwins = 0
        rloss = 0
        rdupe = 0
        rwins = 0
        rloss = 0
        rdupe = 0
        cwins = 0
        closs = 0
        cdupe = 0
        afdupe = 0
        afwins = 0
        afloss = 0
        aidupe = 0
        aiwins = 0
        ailoss = 0
        aidupe = 0
        aiwins = 0
        ailoss = 0
        eddupe = 0
        edwins = 0
        edloss = 0
        eidupe = 0
        eiwins = 0
        eiloss = 0
        mvdupe = 0
        mvwins = 0
        mvloss = 0
        ordupe = 0
        orwins = 0
        orloss = 0
        pbdupe = 0
        pbwins = 0
        pbloss = 0
        rndupe = 0
        rnwins = 0
        rnloss = 0
    if 'monster' in d:
        for m in d['monster']:
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    continue
                elif type(m['srd']) == str:
                    m['original_name']=m['name']
                    m['name'] = m['srd']
            if args.skipua:
                if m['source'].startswith('UA'):
                    if args.verbose:
                        print("Skipping UA Content: ",m['name'])
                    continue
            if args.onlyofficial:
                if m['source'] not in args.onlyofficial:
                    if args.verbose:
                        print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                    continue
            if m['name'] in ['Gar Shatterkeel','Shoalar Quanderil'] and m['source'] == 'LR':
                m['original_name']=m['name']
                m['name'] += "–"+utils.getFriendlySource(m['source'],args)
            if m['name'] in ['Harpy','Felidar','Kraken'] and m['source'] in ['PSX','PSZ']:
                m['original_name']=m['name']
                m['name'] += "–"+utils.getFriendlySource(m['source'],args)
            if m['name'] == 'Darathra Shendrel' and m['source'] == "SKT":
                m['original_name']=m['name']
                m['name'] += "–"+utils.getFriendlySource(m['source'],args)
            if m['name'] == "Demogorgon" and m['source'] == "HftT":
                m['original_name']=m['name']
                m['name'] += " (monstrosity)"
            if m['name'] == "Tressym" and m['source'] == "BGDIA":
                m['original_name']=m['name']
                m['name'] += " (monstrosity)"
            if m['name'] == "Amphisbaena" and m['source'] == "GoS":
                m['original_name']=m['name']
                m['name'] += " (monstrosity)"
            if m['name'] == "Large Mimic" and m['source'] == "RMBRE":
                m['original_name']=m['name']
                m['name'] += " (Multiattack)"
            if m['name'] == "Brain in a Jar" and m['source'] == "LLK":
                m['original_name']=m['name']
                m['name'] += " (Noncore)"
            if m['name'] == "Medusa" and m['source'] == "MOT":
                m['original_name']=m['name']
                m['name'] += " (Theran Variant)"
            if m['name'] == "Ice Troll" and m['source'] == "RoT":
                m['original_name']=m['name']
                m['name'] += " (Variant)"
            if m['source'].startswith('UA'):
                m['original_name'] = m['name']
                m['name'] = m['name'] + " (UA)"
            for xmlmon in compendium.findall("./monster[name='{}']".format(re.sub(r'\'','*',m['name']))):
                if args.verbose or args.showdupe:
                    print ("{0} in {1} is duplicate entry for {2} from {3}".format(m['name'],utils.getFriendlySource(m['source'],args),xmlmon.find('name').text,xmlmon.find('source').text if xmlmon.find('source') != None else '--'))
                mdupe += 1
            if fluff is not None and 'monsterFluff' in fluff:
                if 'entries' in m:
                    m['entries'] += utils.appendFluff(fluff,m['name'])
                else:
                    m['entries'] = utils.appendFluff(fluff,m['name'])
                if 'image' not in m:
                    m['image'] = utils.findFluffImage(fluff,m['name'])
            if ignoreError:
                try:
                    parseMonster(m, compendium, args)
                    mwins += 1
                except Exception:
                    print("FAILED: " + m['name'])
                    mloss += 1
                    continue
            else:
                if args.verbose:
                    print("Parsing " + m['name'])
                parseMonster(m, compendium, args)
                mwins += 1
    if 'vehicle' in d:
        for m in d['vehicle']:
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    continue
                elif type(m['srd']) == str:
                    m['original_name']=m['name']
                    m['name'] = m['srd']
            if args.skipua:
                if m['source'].startswith('UA'):
                    if args.verbose:
                        print("Skipping UA Content: ",m['name'])
                    continue
            if args.onlyofficial:
                if m['source'] not in args.onlyofficial:
                    if args.verbose:
                        print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                    continue
            if m['source'].startswith("UA"):
                m['original_name'] = m['name']
                m['name'] += " (Unearthed Arcana)"
            for xmlmon in compendium.findall("./monster[name='{}']".format(re.sub(r'\'','*',m['name']))):
                if args.verbose or args.showdupe:
                    print ("{0} in {1} is duplicate entry for {2} from {3}".format(m['name'],utils.getFriendlySource(m['source'],args),xmlmon.find('name').text,xmlmon.find('source').text))
                mdupe += 1
            if fluff is not None and 'vehicleFluff' in fluff:
                if 'entries' in m:
                    m['entries'] += utils.appendFluff(fluff,m['name'],'vehicleFluff',args.nohtml)
                else:
                    m['entries'] = utils.appendFluff(fluff,m['name'],'vehicleFluff',args.nohtml)
                if 'image' not in m:
                    m['image'] = utils.findFluffImage(fluff,m['name'],'vehicleFluff')
            if 'alignment' not in m:
                m['alignment'] = [ 'U' ]
            if m['vehicleType'] == "INFWAR":
                m['type'] = "vehicle ({:,d} lb.)".format(m['weight'])
                m['ac'] = [ "{} (19 while motionless)".format(19+utils.getAbilityMod(m["dex"])) ]
                m['hp'] = { "special": "{} (damage threshold {}, mishap threshold {})".format(m['hp']['hp'],m['hp']['dt'],m['hp']['mt']) }
                if 'action' not in m:
                    m['action'] = m['actionStation']
                else:
                    m['action'] += m['actionStation']
                m['speed'] = "{} ft.".format(m['speed'])
            elif m['vehicleType'] == "SHIP":
                m['type'] = "vehicle ({} x {})".format(m['dimensions'][0],m['dimensions'][1])
                m['ac'] = [ m['hull']['ac'] if 'hull' in m else '' ]
                m['hp'] = { "special": str(m['hull']['hp']) if 'hull' in m else '' }
                if not 'trait' in m:
                    m['trait'] = []
                if 'action' not in m:
                    m['action'] = []
                else:
                    m['action'] = [ { "type": "entries", "entries": copy.deepcopy(m['action']) } ]
                if 'hull' in m:
                    if args.nohtml:
                        m['trait'].append({
                            "name": "Hull:",
                            "type": "entries",
                            "entries": [
                                "Armor Class: {}".format(m['hull']['ac']),
                                "Hit Points: {}{}{}".format(m['hull']['hp'],
                                        " (damage threshold {})".format(m['hull']['dt']) if 'dt' in m['hull'] else '',
                                        "; " + m['hull']['hpNote'] if 'hpNote' in m['hull'] else "")
                            ] })
                    else:
                        m['trait'].append({
                            "name": "Hull:",
                            "type": "entries",
                            "entries": [
                                "<i>Armor Class:</i> {}".format(m['hull']['ac']),
                                "<i>Hit Points:</i> {}{}{}".format(m['hull']['hp'],
                                        " (damage threshold {})".format(m['hull']['dt']) if 'dt' in m['hull'] else '',
                                        "; " + m['hull']['hpNote'] if 'hpNote' in m['hull'] else "")
                            ] })
                if 'control' in m:
                    for c in m['control']:
                        if args.nohtml:
                            trait = {
                                "name": "Control:",
                                "type": "entries",
                                "entries": [
                                    "{}".format(c['name']),
                                    "Armor Class: {}".format(c['ac']),
                                    "Hit Points: {}{}{}".format(c['hp'],
                                        " (damage threshold {})".format(c['dt']) if 'dt' in c else '',
                                        "; "+c['hpNote'] if 'hpNote' in c else '')
                                     ]
                                }
                        else:
                            trait = {
                                "name": "Control:",
                                "type": "entries",
                                "entries": [
                                    "<i>{}</i>".format(c['name']),
                                    "<i>Armor Class:</i> {}".format(c['ac']),
                                    "<i>Hit Points:</i> {}{}{}".format(c['hp'],
                                        " (damage threshold {})".format(c['dt']) if 'dt' in c else '',
                                        "; "+c['hpNote'] if 'hpNote' in c else '')
                                     ]
                                }
                        if 'entries' in c:
                            trait['entries'] += c['entries']
                        m['trait'].append(trait)
                if 'movement' in m:
                    for c in m['movement']:
                        if args.nohtml:
                            trait = {
                                "name": "Movement:",
                                "type": "entries",
                                "entries": [
                                    "{}".format(c['name']),
                                    "Armor Class: {}".format(c['ac']),
                                    "Hit Points: {}{}{}".format(c['hp'],
                                        " (damage threshold {})".format(c['dt']) if 'dt' in c else '',
                                        "; "+c['hpNote'] if 'hpNote' in c else '')
                                    ]
                                }
                        else:
                            trait = {
                                "name": "Movement:",
                                "type": "entries",
                                "entries": [
                                    "<i>{}</i>".format(c['name']),
                                    "<i>Armor Class:</i> {}".format(c['ac']),
                                    "<i>Hit Points:</i> {}{}{}".format(c['hp'],
                                        " (damage threshold {})".format(c['dt']) if 'dt' in c else '',
                                        "; "+c['hpNote'] if 'hpNote' in c else '')
                                    ]
                                }
                        if 'locomotion' in c:
                            for l in c['locomotion']:
                                if args.nohtml:
                                    trait['entries'].append("Locomotion ({}): ".format(l['mode']) + "\n".join(l['entries']))
                                else:
                                    trait['entries'].append("<i>Locomotion ({}):</i> ".format(l['mode']) + "\n".join(l['entries']))
                        if 'entries' in c:
                            trait['entries'] += c['entries']
                        m['trait'].append(trait)
                if 'weapon' in m:
                    for c in m['weapon']:
                        if args.nohtml:
                            trait = {
                                "name": "Weapons:",
                                "type": "entries",
                                "entries": [
                                    "{}{}".format(c['name']," ({})".format(c["count"]) if 'count' in c else "")
                                    ]
                                }
                            if 'ac' in c:
                                trait['entries'].append("Armor Class: {}".format(c['ac']))
                            if 'hp' in c:
                                trait['entries'].append("Hit Points: {}{}{}{}".format(
                                    c['hp'],
                                    " (damage threshold {})".format(c['dt']) if 'dt' in c else '',
                                    " each" if 'count' in c and c["count"] > 1 else "",
                                    "; "+c['hpNote'] if 'hpNote' in c else ''))
                        else:
                            trait = {
                                "name": "Weapons:",
                                "type": "entries",
                                "entries": [
                                    "<i>{}{}</i>".format(c['name']," ({})".format(c["count"]) if 'count' in c else "")
                                    ]
                                }
                            if 'ac' in c:
                                trait['entries'].append("<i>Armor Class:</i> {}".format(c['ac']))
                            if 'hp' in c:
                                trait['entries'].append("<i>Hit Points:</i> {}{}{}{}".format(
                                    c['hp'],
                                    " (damage threshold {})".format(c['dt']) if 'dt' in c else '',
                                    " each" if 'count' in c and c["count"] > 1 else "",
                                    "; "+c['hpNote'] if 'hpNote' in c else ''))
                        if 'entries' in c:
                            trait['entries'] += c['entries']
                        m['action'].append(trait)
                m['speed'] = "{} miles per hour ({} miles per day)".format(m['pace'],m['pace']*24)
            else:
                m['type'] = m['vehicleType']
                if 'ac' not in m:
                    m['ac'] = [ { "ac": "Unknown" } ]
            if ignoreError:
                try:
                    parseMonster(m, compendium, args)
                    mwins += 1
                except Exception:
                    print("FAILED: " + m['name'])
                    mloss += 1
                    continue
            else:
                if args.verbose:
                    print("Parsing " + m['name'])
                parseMonster(m, compendium, args)
                mwins += 1
    if 'spell' in d:
        for m in d['spell']:
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    continue
                elif type(m['srd']) == str:
                    m['original_name']=m['name']
                    m['name'] = m['srd']
            if args.skipua:
                if m['source'].startswith('UA'):
                    if args.verbose:
                        print("Skipping UA Content: ",m['name'])
                    continue
            if args.onlyofficial:
                # Check sources for classes instead of spell
                if not utils.checkOfficialSpell(m, args):
                    if args.verbose:
                        print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                    continue
            if m['source'].startswith('UA'):
                m['original_name'] = m['name']
                m['name'] = m['name'] + " (UA)"
            for xmlmon in compendium.findall("./spell[name='{}']".format(re.sub(r'\'','*',m['name']))):
                if args.verbose or args.showdupe:
                    print ("Found duplicate entry for {} from {}".format(m['name'],xmlmon.find('source').text if xmlmon.find('source') != None else '--'))
                sdupe += 1

            if ignoreError:
                try:
                    parseSpell(m, compendium, args)
                    swins += 1
                except Exception:
                    print("FAILED: " + m['name'])
                    sloss += 1
                    continue
            else:
                if args.verbose:
                    print("Parsing " + m['name'])
                parseSpell(m, compendium, args)
                swins += 1
    if 'background' in d:
        for m in d['background']:
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    continue
                elif type(m['srd']) == str:
                    m['original_name']=m['name']
                    m['name'] = m['srd']
            if args.skipua:
                if m['source'].startswith('UA'):
                    if args.verbose:
                        print("Skipping UA Content: ",m['name'])
                    continue
            if args.onlyofficial:
                if m['source'] not in args.onlyofficial:
                    if args.verbose:
                        print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                    continue
            for xmlmon in compendium.findall("./background[name='{}']".format(re.sub(r'\'','*',m['name']))):
                if args.verbose or args.showdupe:
                    print ("Found duplicate entry for {} from {}".format(m['name'],xmlmon.find('source').text if xmlmon.find('source') != None else '--'))
                bdupe += 1
            if fluff is not None and 'backgroundFluff' in fluff:
                if 'entries' in m:
                    m['entries'] = utils.appendFluff(fluff,m['name'],'backgroundFluff',args.nohtml) + m['entries']
                else:
                    m['entries'] = utils.appendFluff(fluff,m['name'],'backgroundFluff',args.nohtml)
                if 'image' not in m:
                    m['image'] = utils.findFluffImage(fluff,m['name'],'backgroundFluff')
            if ignoreError:
                try:
                    parseBackground(m, compendium, args)
                    bwins += 1
                except Exception:
                    print("FAILED: " + m['name'])
                    bloss += 1
                    continue
            else:
                if args.verbose:
                    print("Parsing " + m['name'])
                parseBackground(m, compendium, args)
                bwins += 1

    if 'feat' in d:
        for m in d['feat']:
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    continue
                elif type(m['srd']) == str:
                    m['original_name']=m['name']
                    m['name'] = m['srd']
            if args.skipua:
                if m['source'].startswith('UA'):
                    if args.verbose:
                        print("Skipping UA Content: ",m['name'])
                    continue
            if args.onlyofficial:
                if m['source'] not in args.onlyofficial:
                    if args.verbose:
                        print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                    continue
            if m['source'].startswith('UA'):
                m['original_name'] = m['name']
                m['name'] = m['name'] + " (UA)"
            for xmlmon in compendium.findall("./feat[name='{}']".format(re.sub(r'\'','*',m['name']))):
                if args.verbose or args.showdupe:
                    print ("Found duplicate entry for {}".format(m['name']))
                fdupe += 1

            if ignoreError:
                try:
                    parseFeat(m, compendium, args)
                    fwins += 1
                except Exception:
                    print("FAILED: " + m['name'])
                    floss += 1
                    continue
            else:
                if args.verbose:
                    print("Parsing " + m['name'])
                parseFeat(m, compendium, args)
                fwins += 1

    if 'race' in d:
        for race in d['race']:
            m = copy.deepcopy(race)
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    if 'subraces' in m:
                        hasSRD = False
                        for sr in m['subraces']:
                            if 'srd' in sr:
                                hasSRD = True
                                break
                        if not hasSRD:
                            continue
                    else:
                        continue
                elif type(m['srd']) == str:
                    m['original_name']=m['name']
                    m['name'] = m['srd']
            if args.skipua:
                if m['source'].startswith('UA'):
                    if args.verbose:
                        print("Skipping UA Content: ",m['name'])
                    continue
            if args.onlyofficial:
                if m['source'] not in args.onlyofficial:
                    if args.verbose:
                        print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                    continue
            if m['source'].startswith('UA'):
                m['original_name'] = m['name']
                if m['source'] == "UARacesOfEberron":
                    m['name'] = m['name'] + " (UA Races of Eberron)"
                else:
                    m['name'] = m['name'] + " (UA)"
            elif m['source'] == "DMG":
                m['original_name'] = m['name']
                m['name'] = m['name'] + " (DMG)"
            elif m['source'] == "PSK" and m['name'] == "Vedalken":
                m['original_name'] = m['name']
                m['name'] = m['name'] + " (Kaladesh)"
            elif m['source'] == "MOT":
                if m['name'] in ("Centaur","Minotaur","Triton"):
                    m['original_name'] = m['name']
                    m['name'] = m['name'] + " (Theros)"
            if fluff is not None and 'race' in fluff:
                if 'entries' in m:
                    m['entries'] += utils.appendFluff(fluff,m['name'],'raceFluff',args.nohtml)
                else:
                    m['entries'] = utils.appendFluff(fluff,m['name'],'raceFluff',args.nohtml)
                if 'image' not in m:
                    m['image'] = utils.findFluffImage(fluff,m['name'],'raceFluff')
            if 'subraces' in m:
                for sub in m['subraces']:
                    if args.srd:
                        if 'srd' not in sub or not sub['srd']:
                            continue
                        elif type(sub['srd']) == str:
                            sub['original_name']=sub['name']
                            sub['name'] = sub['srd']
                    if args.skipua:
                        if 'source' in sub and sub['source'].startswith('UA'):
                            if args.verbose:
                                print("Skipping UA Content: Subrace ",sub['name'] if 'name' in sub else m['name'])
                            continue
                    if args.onlyofficial:
                        if 'source' in sub and sub['source'] not in args.onlyofficial:
                            if args.verbose:
                                print("Skipping unoffical content: {} from {}".format(sub['name'],utils.getFriendlySource(sub['source'],args)))
                            continue
                    sr = copy.deepcopy(m)
                    if "source" in sub and "source" in sr:
                        del sr["source"]
                    if "page" in sub and "page" in sr:
                        del sr["page"]
                    if "name" not in sub:
                        if "source" in sub and "source" not in sr:
                            if sub["source"] == "GGR":
                                sr["name"] += " (Ravnica)"
                            elif sub["source"] == "ERLW":
                                sr["name"] += " (Eberron)"
                            elif sub["source"].startswith("UA"):
                                sr["name"] += " (UA)"
                    for k,v in sub.items():
                        if k == "name":
                            if "source" in sub and sub["source"].startswith("UA"):
                                sr['name'] += " ({}–UA)".format(v)
                            elif "source" in sub and sub["source"] == "DMG":
                                sr['name'] += " ({}–DMG)".format(v)
                            else:
                                sr['name'] += " ({})".format(v)
                        elif k == "ability" in sub and "ability" in sr:
                            sr["ability"] += v
                        elif k == "entries":
                            insertpoint = 0
                            for e in v:
                                if "data" in e:
                                    if "overwrite" not in e["data"] and "replace" in e["data"]:
                                        e["data"]["overwrite"] = e["data"]["replace"]
                                    for en in sr["entries"]:
                                        if type(en) == dict and "name" in en and en["name"] == e["data"]["overwrite"]:
                                            en["name"] = e["name"]
                                            en["entries"] = e["entries"]
                                else:
                                    sr["entries"].insert(insertpoint,e)
                                    insertpoint += 1
                        else:
                            sr[k] = v
                    for xmlmon in compendium.findall("./race[name='{}']".format(re.sub(r'\'','*',sr['name']))):
                        if args.verbose or args.showdupe:
                            print ("Found duplicate entry for {}".format(sr['name']))
                        rdupe += 1
                    if ignoreError:
                        try:
                            parseRace(sr, compendium, args)
                            rwins += 1
                        except Exception:
                            print("FAILED: " + sr['name'])
                            rloss += 1
                            continue
                    else:
                        if args.verbose:
                            print("Parsing " + sr['name'])
                        parseRace(sr, compendium, args)
                        rwins += 1
            else:
                for xmlmon in compendium.findall("./race[name='{}']".format(re.sub(r'\'','*',m['name']))):
                    if args.verbose or args.showdupe:
                        print ("Found duplicate entry for {}".format(m['name']))
                    rdupe += 1
                if ignoreError:
                    try:
                        parseRace(m, compendium, args)
                        rwins += 1
                    except Exception:
                        print("FAILED: " + m['name'])
                        rloss += 1
                        continue
                else:
                    if args.verbose:
                        print("Parsing " + m['name'])
                    parseRace(m, compendium, args)
                    rwins += 1
    if 'class' in d:
        for m in d['class']:
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    continue
                elif type(m['srd']) == str:
                    m['original_name']=m['name']
                    m['name'] = m['srd']
            if args.skipua:
                if m['source'].startswith('UA'):
                    if args.verbose:
                        print("Skipping UA Content: ",m['name'])
                    continue
            if args.onlyofficial:
                # Check sources in subclasses instead of class
                isOfficial = False
                for subclass in m['subclasses']:
                    if subclass['source'] in args.onlyofficial:
                        isOfficial = True
                        break
                # Exception for Ranger variants
                if (m['name'] in ["Ranger (Spell-less)", "Ranger (Ambuscade)", "Ranger (Revised)"]) and \
                    m['source'] not in args.onlyofficial:
                    isOfficial = False
                elif (m['name'] == "Ranger (Spell-less)" and m['source'] == "UAModifyingClasses") or \
                    (m['name'] == "Ranger (Ambuscade)" and m['source'] == "UARanger") or \
                    (m['name'] == "Ranger (Revised)" and m['source'] == "UATheRangerRevised"):
                    isOfficial = True
                if not isOfficial:
                    if args.verbose:
                        print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                    continue
            if 'classFeature' not in m:
                m['classFeature'] = d['classFeature']
            if 'subclassFeature' not in m and 'subclassFeature' in d:
                m['subclassFeature'] = d['subclassFeature']

            if m['source'].startswith('UA'):
                m['original_name'] = m['name']
                m['name'] = m['name'] + " (UA)"
            for xmlmon in compendium.findall("./class[name='{}']".format(re.sub(r'\'','*',m['name']))):
                if args.verbose or args.showdupe:
                    print ("Found duplicate entry for {}".format(m['name']))
                cdupe += 1
            if ignoreError:
                try:
                    parseClass(m, compendium, args)
                    cwins += 1
                except Exception:
                    print("FAILED: " + m['name'])
                    closs += 1
                    continue
            else:
                if args.verbose:
                    print("Parsing " + m['name'])
                parseClass(m, compendium, args)
                cwins += 1
    if 'item' in d:
        for m in d['item']:
            if 'age' in m and m['age'].lower() in excludedages:
                if args.verbose:
                    print ("SKIPPING",m['age'],"ITEM:",m['name'])
                continue
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    continue
                elif type(m['srd']) == str:
                    m['original_name']=m['name']
                    m['name'] = m['srd']
            if args.skipua:
                if m['source'].startswith('UA'):
                    if args.verbose:
                        print("Skipping UA Content: ",m['name'])
                    continue
            if args.onlyofficial:
                if m['source'] not in args.onlyofficial:
                    if args.verbose:
                        print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                    continue
            if m['name'] == "Trinket" and m['source'] == "CoS":
                m['name'] += " (Gothic)"
            elif m['name'] == "Trinket" and m['source'] == "EET":
                m['name'] += " (Elemental Evil)"
            elif m['name'] == "Trinket" and m['source'] == "AI":
                m['name'] += " (Acquisitions Incorporated)"
            elif m['name'] == "Ioun Stone" and m['source'] == "LLK":
                m['name'] += " (Kwalish)"
            if m['source'].startswith('UA'):
                m['original_name'] = m['name']
                m['name'] = m['name'] + " (UA)"
            for xmlmon in compendium.findall("./item[name='{}']".format(re.sub(r'\'','*',m['name']))):
                if args.verbose or args.showdupe:
                    print ("Found duplicate entry for {} from {}".format(m['name'],xmlmon.find('source').text if xmlmon.find('source') != None else '--'))
                idupe += 1

            if ignoreError:
                try:
                    parseItem(m, compendium, args)
                    iwins += 1
                except Exception:
                    print("FAILED: " + m['name'])
                    iloss += 1
                    continue
            else:
                if args.verbose:
                    print("Parsing " + m['name'])
                parseItem(m, compendium, args)
                iwins += 1
    if 'itemGroup' in d:
        for m in d['itemGroup']:
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    continue
                elif type(m['srd']) == str:
                    m['original_name']=m['name']
                    m['name'] = m['srd']
            if args.onlyofficial:
                if m['source'] not in args.onlyofficial:
                    if args.verbose:
                        print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                    continue
            if ignoreError:
                try:
                    parseItem(m, compendium, args)
                    iwins += 1
                except Exception:
                    print("FAILED: " + m['name'])
                    iloss += 1
                    continue
            else:
                if args.verbose:
                    print("Parsing " + m['name'])
                parseItem(m, compendium, args)
                iwins += 1
    if 'baseitem' in d:
        for m in d['baseitem']:
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    continue
                elif type(m['srd']) == str:
                    m['original_name']=m['name']
                    m['name'] = m['srd']
            if 'age' in m and m['age'].lower() in excludedages:
                if args.verbose:
                    print ("SKIPPING",m['age'],"ITEM:",m['name'])
                continue
            if ignoreError:
                try:
                    parseItem(copy.deepcopy(m), compendium, args)
                    iwins += 1
                except Exception:
                    print("FAILED: " + m['name'])
                    iloss += 1
                    continue
            else:
                if args.verbose:
                    print("Parsing " + m['name'])
                parseItem(copy.deepcopy(m), compendium, args)
                iwins += 1
        with open("./data/magicvariants.json",encoding='utf-8') as f:
            mv = json.load(f)
            f.close()
        if 'variant' in mv:
            for v in mv['variant']:
                if args.srd:
                    if 'srd' not in v['inherits'] or not v['inherits']['srd']:
                        continue
                if 'age' in m and m['age'].lower() in excludedages:
                    if args.verbose:
                        print ("SKIPPING",m['age'],"ITEM:",m['name'])
                    continue
                if args.verbose:
                    print("Processing Variants: " + v['name'])
                for req in v['requires']:
                    for m in d['baseitem']:
                        if 'age' in m and m['age'].lower() in excludedages:
                            if args.verbose:
                                print ("SKIPPING",m['age'],"ITEM:",m['name'])
                            continue
                        if args.srd:
                            req["srd"] = True
                        itemMatch = all([k in m and m[k] == req[k] for k in req])
                        if 'excludes' in v:
                            for ex in v['excludes']:
                                if type(v['excludes'][ex]) == list:
                                    if any(sub in m[ex] for sub in v['excludes'][ex]): itemMatch = False
                                elif ex in m and type(v['excludes'][ex]) != str:
                                    if v['excludes'][ex] == m[ex]:
                                        itemMatch = False
                                elif ex in m and v['excludes'][ex] in m[ex]:
                                    itemMatch = False
                        if not itemMatch:
                            continue
                        else:
                            if 'items' not in v:
                                v['items'] = []
                            if args.verbose:
                                print ("Creating",v['name'],"for",m['name'])
                            mm = copy.deepcopy(m)
                            if 'value' in mm:
                                del mm['value']
                            mm['baseName'] = mm['name']
                            #if 'entries' in v and 'entries' in m:
                            #    mm['entries'] = v['entries'] + m['entries']
                            #elif 'entries' in v :
                            #    mm['entries'] = [] + v['entries']
                            for inheritk in v['inherits']:
                                inherit = copy.deepcopy(v['inherits'][inheritk])
                                if inheritk == 'entries' and 'entries' in mm:
                                    mm['entries'] += inherit
                                elif inheritk == 'entries':
                                    mm['entries'] = inherit 
                                elif inheritk == 'namePrefix':
                                    mm['name'] = inherit + mm['name']
                                elif inheritk == 'nameSuffix':
                                    mm['name'] = mm['name'] + inherit
                                else:
                                    mm[inheritk] = inherit
                                    v[inheritk] = inherit
                            v['items'].append(mm['name'])
                            if mm['name'] in mv['linkedLootTables']['DMG']:
                                if 'lootTables' not in mm:
                                    mm['lootTables'] = []
                                mm['lootTables'] += mv['linkedLootTables']['DMG'][mm['name']]
                        if args.srd:
                            if 'srd' not in mm or not mm['srd']:
                                continue
                            elif type(mm['srd']) == str:
                                mm['original_name']=mm['name']
                                mm['name'] = mm['srd']
                        if ignoreError:
                            try:
                                parseItem(mm, compendium, args)
                                iwins += 1
                            except Exception:
                                print("FAILED: " + mm['name'])
                                iloss += 1
                                continue
                        else:
                            if args.verbose:
                                print("Parsing " + mm['name'],len(mm))
                            parseItem(mm, compendium, args)
                            iwins += 1
                if 'items' in v and len(v['items']) > 1 and not args.nohtml:
                    if ignoreError:
                        try:
                            parseItem(v, compendium, args)
                            iwins += 1
                        except Exception:
                            print("FAILED: " + v['name'])
                            iloss += 1
                            continue
                    else:
                        if args.verbose:
                            print("Parsing " + v['name'],len(v))
                        parseItem(v, compendium, args)
                        iwins += 1

    if 'optionalfeature' in d:
        for m in d['optionalfeature']:
            fTypes = set()
            if type(m['featureType']) != list:
                fTypes.add(m['featureType'].split(':')[0])
            else:
                for t in m['featureType']:
                    fTypes.add(t.split(':')[0])
            
            if args.srd:
                if 'srd' not in m or not m['srd']:
                    continue
                elif type(m['srd']) == str:
                    m['original_name'] = m['name']
                    m['name'] = m['srd']
            if args.skipua:
                if m['source'].startswith('UA'):
                    if args.verbose:
                        print("Skipping UA Content: ",m['name'])
                    continue
            if args.onlyofficial:
                if m['source'] not in args.onlyofficial:
                    if args.verbose:
                        print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                    continue
            if m['source'].startswith('UA'):
                m['original_name'] = m['name']
                m['name'] = m['name'] + " (UA)"

            for fType in fTypes:
                if fType not in ["AF", "AI", "AS", "ED", "EI", "MV", "OR", "PB", "RN"]:
                    continue

                if fType == "AF": m['name'] = "Formula: " + m['name']
                elif fType == "AI": m['name'] = "Infusion: " + m['name']
                elif fType == "AS": m['name'] = "Arcane Shot: " + m['name']
                elif fType == "ED": m['name'] = "Elemental Discipline: " + m['name']
                elif fType == "EI": m['name'] = "Invocation: " + m['name']
                elif fType == "MV": m['name'] = "Maneuver: " + m['name']
                elif fType == "OR": m['name'] = "Resonant: " + m['name']
                elif fType == "PB": m['name'] = "Pact Boon: " + m['name']
                elif fType == "RN": m['name'] = "Rune: " + m['name']

                for xmlmon in compendium.findall("./feat[name='{}']".format(re.sub(r'\'','*',m['name']))):
                    if args.verbose or args.showdupe:
                        print ("Found duplicate entry for {} from {}".format(m['name'],xmlmon.find('source').text if xmlmon.find('source') != None else '--'))
                    if fType == "AF": afdupe += 1
                    elif fType == "AI": aidupe += 1
                    elif fType == "AS": asdupe += 1
                    elif fType == "ED": eddupe += 1
                    elif fType == "EI": eidupe += 1
                    elif fType == "MV": mvdupe += 1
                    elif fType == "OR": mvdupe += 1
                    elif fType == "PB": pbdupe += 1
                    elif fType == "RN": rndupe += 1
                
                if ignoreError:
                    try:
                        parseFeature(m, compendium, args)
                        if fType == "AF": afwins += 1
                        elif fType == "AI": aiwins += 1
                        elif fType == "AS": aswins += 1
                        elif fType == "ED": edwins += 1
                        elif fType == "EI": eiwins += 1
                        elif fType == "MV": mvwins += 1
                        elif fType == "OR": mvwins += 1
                        elif fType == "PB": pbwins += 1
                        elif fType == "RN": rnwins += 1
                    except Exception:
                        print("FAILED: " + m['name'])
                        if fType == "AF": afloss += 1
                        elif fType == "AI": ailoss += 1
                        elif fType == "AI": asloss += 1
                        elif fType == "ED": edloss += 1
                        elif fType == "EI": eiloss += 1
                        elif fType == "MV": mvloss += 1
                        elif fType == "OR": mvloss += 1
                        elif fType == "PB": pbloss += 1
                        elif fType == "RN": rnloss += 1
                        continue
                else:
                    if args.verbose:
                        print("Parsing " + m['name'])
                    parseFeature(m, compendium, args)
                    if fType == "AF": afwins += 1
                    elif fType == "AI": aiwins += 1
                    elif fType == "AS": aswins += 1
                    elif fType == "ED": edwins += 1
                    elif fType == "EI": eiwins += 1
                    elif fType == "MV": mvwins += 1
                    elif fType == "OR": mvwins += 1
                    elif fType == "PB": pbwins += 1
                    elif fType == "RN": rnwins += 1

    print("Done converting " + os.path.splitext(file)[0])

    if not args.combinedoutput:
        if mwins > 0 or mloss > 0:
            print("Converted {}/{} monsters (failed {})".format(mwins, mwins +
                                                            mloss, mloss) if ignoreError else "Converted {} monsters".format(mwins))
            if mdupe > 0: print(" ({} duplicate{})".format(mdupe,"s" if mdupe > 1 else ""))
        if swins > 0 or sloss > 0:
            print("Converted {}/{} spells (failed {})".format(swins, swins +
                                                            sloss, sloss) if ignoreError else "Converted {} spells".format(swins))
            if sdupe > 0: print(" ({} duplicate{})".format(sdupe,"s" if sdupe > 1 else ""))
        if cwins > 0 or closs > 0:
            print("Converted {}/{} classes (failed {})".format(cwins, cwins +
                                                            closs, closs) if ignoreError else "Converted {} classes".format(cwins))
            if cdupe > 0: print(" ({} duplicate{})".format(cdupe,"s" if cdupe > 1 else ""))
        if iwins > 0 or iloss > 0:
            print("Converted {}/{} items (failed {})".format(iwins, iwins +
                                                            iloss, iloss) if ignoreError else "Converted {} items".format(iwins))
            if idupe > 0: print(" ({} duplicate{})".format(idupe,"s" if idupe > 1 else ""))
        if bwins > 0 or bloss > 0:
            print("Converted {}/{} backgrounds (failed {})".format(bwins, bwins +
                                                            bloss, bloss) if ignoreError else "Converted {} backgrounds".format(bwins))
            if bdupe > 0: print(" ({} duplicate{})".format(bdupe,"s" if bdupe > 1 else ""))
        if fwins > 0 or floss > 0:
            print("Converted {}/{} feats (failed {})".format(fwins, fwins +
                                                            floss, floss) if ignoreError else "Converted {} feats".format(fwins))
            if fdupe > 0: print(" ({} duplicate{})".format(fdupe,"s" if fdupe > 1 else ""))
        if rwins > 0 or rloss > 0:
            print("Converted {}/{} races (failed {})".format(rwins, rwins +
                                                            rloss, rloss) if ignoreError else "Converted {} races".format(rwins))
            if rdupe > 0: print(" ({} duplicate{})".format(rdupe,"s" if rdupe > 1 else ""))
        if afwins > 0 or afloss > 0:
            print("Converted {}/{} formulas (failed {})".format(afwins, afwins +
                                                            afloss, afloss) if ignoreError else "Converted {} formulas".format(afwins))
            if afdupe > 0: print(" ({} duplicate{})".format(afdupe,"s" if afdupe > 1 else ""))
        if aiwins > 0 or ailoss > 0:
            print("Converted {}/{} infusions (failed {})".format(aiwins, aiwins +
                                                            ailoss, ailoss) if ignoreError else "Converted {} infusions".format(aiwins))
            if aidupe > 0: print(" ({} duplicate{})".format(aidupe,"s" if aidupe > 1 else ""))
        if aswins > 0 or asloss > 0:
            print("Converted {}/{} arcane shots (failed {})".format(aswins, aswins +
                                                            asloss, asloss) if ignoreError else "Converted {} arcane shots".format(aswins))
            if asdupe > 0: print(" ({} duplicate{})".format(asdupe,"s" if asdupe > 1 else ""))
        if edwins > 0 or edloss > 0:
            print("Converted {}/{} elemental disciplines (failed {})".format(edwins, edwins +
                                                            edloss, edloss) if ignoreError else "Converted {} elemental disciplines".format(edwins))
            if eddupe > 0: print(" ({} duplicate{})".format(eddupe,"s" if eddupe > 1 else ""))
        if eiwins > 0 or eiloss > 0:
            print("Converted {}/{} invocations (failed {})".format(eiwins, eiwins +
                                                            eiloss, eiloss) if ignoreError else "Converted {} invocations".format(eiwins))
            if eidupe > 0: print(" ({} duplicate{})".format(eidupe,"s" if eidupe > 1 else ""))
        if mvwins > 0 or mvloss > 0:
            print("Converted {}/{} maneuvers (failed {})".format(mvwins, mvwins +
                                                            mvloss, mvloss) if ignoreError else "Converted {} maneuvers".format(mvwins))
            if mvdupe > 0: print(" ({} duplicate{})".format(mvdupe,"s" if mvdupe > 1 else ""))
        if orwins > 0 or orloss > 0:
            print("Converted {}/{} resonants (failed {})".format(orwins, orwins +
                                                            orloss, orloss) if ignoreError else "Converted {} resonants".format(orwins))
            if ordupe > 0: print(" ({} duplicate{})".format(ordupe,"s" if ordupe > 1 else ""))
        if pbwins > 0 or pbloss > 0:
            print("Converted {}/{} pact boons (failed {})".format(pbwins, pbwins +
                                                            pbloss, pbloss) if ignoreError else "Converted {} pact boons".format(pbwins))
            if pbdupe > 0: print(" ({} duplicate{})".format(pbdupe,"s" if pbdupe > 1 else ""))
        if rnwins > 0 or rnloss > 0:
            print("Converted {}/{} runes (failed {})".format(rnwins, rnwins +
                                                            rnloss, rnloss) if ignoreError else "Converted {} runes".format(rnwins))
            if rndupe > 0: print(" ({} duplicate{})".format(rndupe,"s" if rndupe > 1 else ""))
        

        # write to file
        tree = ET.ElementTree(utils.indent(compendium, 1))
        tree.write(
            os.path.splitext(file)[0] +
            ".xml",
            xml_declaration=True,
            short_empty_elements=False,
            encoding='utf-8')
if args.combinedoutput:
    if mwins > 0 or mloss > 0:
        print("Converted {}/{} monsters (failed {})".format(mwins, mwins + mloss,
                                                        mloss) if ignoreError else "Converted {} monsters".format(mwins))
        if mdupe > 0: print(" ({} duplicate{})".format(mdupe,"s" if mdupe > 1 else ""))
    if swins > 0 or sloss > 0:
        print("Converted {}/{} spells (failed {})".format(swins, swins + sloss,
                                                        sloss) if ignoreError else "Converted {} spells".format(swins))
        if sdupe > 0: print(" ({} duplicate{})".format(sdupe,"s" if sdupe > 1 else ""))
    if cwins > 0 or closs > 0:
        print("Converted {}/{} classes (failed {})".format(cwins, cwins + closs,
                                                        closs) if ignoreError else "Converted {} classes".format(cwins))
        if cdupe > 0: print(" ({} duplicate{})".format(cdupe,"s" if cdupe > 1 else ""))
    if iwins > 0 or iloss > 0:
        print("Converted {}/{} items (failed {})".format(iwins, iwins + iloss,
                                                        iloss) if ignoreError else "Converted {} items".format(iwins))
        if idupe > 0: print(" ({} duplicate{})".format(idupe,"s" if idupe > 1 else ""))
    if bwins > 0 or bloss > 0:
        print("Converted {}/{} backgrounds (failed {})".format(bwins, bwins +
                                                        bloss, bloss) if ignoreError else "Converted {} backgrounds".format(bwins))
        if bdupe > 0: print(" ({} duplicate{})".format(bdupe,"s" if bdupe > 1 else ""))
    if fwins > 0 or floss > 0:
        print("Converted {}/{} feats (failed {})".format(fwins, fwins +
                                                        floss, floss) if ignoreError else "Converted {} feats".format(fwins))
        if fdupe > 0: print(" ({} duplicate{})".format(fdupe,"s" if fdupe > 1 else ""))
    if rwins > 0 or rloss > 0:
        print("Converted {}/{} races (failed {})".format(rwins, rwins +
                                                        rloss, rloss) if ignoreError else "Converted {} races".format(rwins))
        if rdupe > 0: print(" ({} duplicate{})".format(rdupe,"s" if rdupe > 1 else ""))
    if afwins > 0 or afloss > 0:
        print("Converted {}/{} formulas (failed {})".format(afwins, afwins +
                                                        afloss, afloss) if ignoreError else "Converted {} formulas".format(afwins))
        if afdupe > 0: print(" ({} duplicate{})".format(afdupe,"s" if afdupe > 1 else ""))
    if aiwins > 0 or ailoss > 0:
        print("Converted {}/{} infusions (failed {})".format(aiwins, aiwins +
                                                        ailoss, ailoss) if ignoreError else "Converted {} infusions".format(aiwins))
        if aidupe > 0: print(" ({} duplicate{})".format(aidupe,"s" if aidupe > 1 else ""))
    if aswins > 0 or asloss > 0:
        print("Converted {}/{} arcane shots (failed {})".format(aswins, aswins +
                                                        asloss, asloss) if ignoreError else "Converted {} arcane shots".format(aswins))
        if asdupe > 0: print(" ({} duplicate{})".format(asdupe,"s" if asdupe > 1 else ""))
    if edwins > 0 or edloss > 0:
        print("Converted {}/{} elemental disciplines (failed {})".format(edwins, edwins +
                                                        edloss, edloss) if ignoreError else "Converted {} elemental disciplines".format(edwins))
        if eddupe > 0: print(" ({} duplicate{})".format(eddupe,"s" if eddupe > 1 else ""))
    if eiwins > 0 or eiloss > 0:
        print("Converted {}/{} invocations (failed {})".format(eiwins, eiwins +
                                                        eiloss, eiloss) if ignoreError else "Converted {} invocations".format(eiwins))
        if eidupe > 0: print(" ({} duplicate{})".format(eidupe,"s" if eidupe > 1 else ""))
    if mvwins > 0 or mvloss > 0:
        print("Converted {}/{} maneuvers (failed {})".format(mvwins, mvwins +
                                                        mvloss, mvloss) if ignoreError else "Converted {} maneuvers".format(mvwins))
        if mvdupe > 0: print(" ({} duplicate{})".format(mvdupe,"s" if mvdupe > 1 else ""))
    if orwins > 0 or orloss > 0:
        print("Converted {}/{} resonants (failed {})".format(orwins, orwins +
                                                        orloss, orloss) if ignoreError else "Converted {} resonants".format(orwins))
        if ordupe > 0: print(" ({} duplicate{})".format(ordupe,"s" if ordupe > 1 else ""))
    if pbwins > 0 or pbloss > 0:
        print("Converted {}/{} pact boons (failed {})".format(pbwins, pbwins +
                                                        pbloss, pbloss) if ignoreError else "Converted {} pact boons".format(pbwins))
        if pbdupe > 0: print(" ({} duplicate{})".format(pbdupe,"s" if pbdupe > 1 else ""))
    if rnwins > 0 or rnloss > 0:
        print("Converted {}/{} runes (failed {})".format(rnwins, rnwins +
                                                        rnloss, rnloss) if ignoreError else "Converted {} runes".format(rnwins))
        if rndupe > 0: print(" ({} duplicate{})".format(rndupe,"s" if rndupe > 1 else ""))

    # write to file
    tree = ET.ElementTree(utils.indent(compendium, 1))
    if args.combinedoutput.endswith(".compendium"):
        if mwins == 0 and swins == 0 and iwins == 0:
            print ("Nothing to output")
        else:
            tree.write(os.path.join(args.tempdir,"compendium.xml"), xml_declaration=True, short_empty_elements=False, encoding='utf-8')
            zipfile = shutil.make_archive(args.combinedoutput,"zip",args.tempdir)
            shutil.move(zipfile,args.combinedoutput)
            if tempdir:
                tempdir.cleanup()
    else:
        if mwins == 0 and swins == 0 and iwins == 0 and fwins == 0 and bwins == 0 and rwins == 0 and cwins == 0 and \
            afwins == 0 and aiwins == 0 and aswins == 0 and edwins == 0 and eiwins == 0 and mvwins == 0 and orwins == 0 and pbwins == 0 and rnwins == 0:
            print("Nothing to output")
        else:
            tree.write(args.combinedoutput, xml_declaration=True, short_empty_elements=False, encoding='utf-8')

# vim: set tabstop=8 softtabstop=0 expandtab shiftwidth=4 smarttab : #
import xml.etree.cElementTree as ET
import re
import utils
import json
import os
import copy
from slugify import slugify
from shutil import copyfile

def parseMonster(m, compendium, args):
    if '_copy' in m:
        if args.verbose:
            print("COPY: " + m['name'] + " from " + m['_copy']['name'] + " in " + m['_copy']['source'])
        xtrsrc = "./data/bestiary/bestiary-" + m['_copy']['source'].lower() + ".json"
        try:
            with open(xtrsrc,encoding='utf-8') as f:
                d = json.load(f)
                f.close()
            mcpy = copy.deepcopy(m)
            for mn in d['monster']:
                if mn['name'].lower() == mcpy['_copy']['name'].lower():
                    if '_copy' in mn:
                        if args.verbose:
                            print("ANOTHER COPY: " + mn['name'] + " from " + mn['_copy']['name'] + " in " + mn['_copy']['source'])
                        xtrsrc2 = "./data/bestiary/bestiary-" + mn['_copy']['source'].lower() + ".json"
                        with open(xtrsrc2,encoding='utf-8') as f:
                            d2 = json.load(f)
                            f.close()
                        for mn2 in d2['monster']:
                            if mn2['name'] == mn['_copy']['name']:
                                mn = copy.deepcopy(mn2)
                                break
                    m = copy.deepcopy(mn)
                    m['name'] = mcpy['name']
                    if 'isNpc' in mcpy:
                        m['isNpc'] = mcpy['isNpc']
                    m['source'] = mcpy['source']
                    if "otherSources" in mcpy:
                        m["otherSources"] = mcpy["otherSources"]
                    elif "otherSources" in m:
                        del m["otherSources"]
                    if 'size' in mcpy:
                        m['size'] = mcpy['size']
                    if 'hp' in mcpy:
                        m['hp'] = mcpy['hp']
                    if 'original_name' in mcpy:
                        m['original_name'] = mcpy['original_name']
                    if 'page' in mcpy:
                        m['page'] = mcpy['page']
                    elif 'page' in m:
                        del m['page']
                    if 'image' in mcpy:
                        m['image'] = mcpy['image']
                    if '_mod' in mcpy['_copy']:
                        m = utils.modifyMonster(m,mcpy['_copy']['_mod'])
                    break
            if '_trait' in mcpy['_copy']:
                if args.verbose:
                    print("Adding extra traits for: " + mcpy['_copy']['_trait']['name'])
                traits = "./data/bestiary/traits.json"
                with open(traits,encoding='utf-8') as f:
                    d = json.load(f)
                    f.close()
                for trait in d['trait']:
                    if trait['name'] == mcpy['_copy']['_trait']['name']:
                        if '_mod' in trait['apply']:
                            m = utils.modifyMonster(m,trait['apply']['_mod'])
                        if '_root' in trait['apply']:
                            for key in trait['apply']['_root']:
                                if key == "speed" and type(trait['apply']['_root'][key]) == int:
                                    for k2 in m['speed']:
                                            m['speed'][k2]=trait['apply']['_root'][key]
                                else:
                                    m[key] = trait['apply']['_root'][key]
        except IOError as e:
            if args.verbose:
                print ("Could not load additional source ({}): {}".format(e.errno, e.strerror))
            return
#    for eachmonsters in compendium.findall('monster'):
#        if eachmonsters.find('name').text == m['name']:
#            m['name'] = "{} (DUPLICATE IN {})".format(m['name'],m['source'])
    monster = ET.SubElement(compendium, 'monster')
    name = ET.SubElement(monster, 'name')
    name.text = m['name']

    size = ET.SubElement(monster, 'size')
    size.text = m['size']

    typ = ET.SubElement(monster, 'type')
    if isinstance(m['type'], dict):
        if 'swarmSize' in m['type']:
            typ.text = "swarm of {} {}s".format(
                utils.convertSize(m['size']), m['type']['type'])
        elif 'tags' in m['type']:
            subtypes = []
            for tag in m['type']['tags']:
                if not isinstance(tag, dict):
                    subtypes.append(tag)
                else:
                    subtypes.append(tag['prefix'] + tag['tag'])
            typ.text = "{} ({})".format(m['type']['type'], ", ".join(subtypes))
        else:
            typ.text = m['type']['type']
    else:
        typ.text = m['type']

    alignment = ET.SubElement(monster, 'alignment')
    if 'alignment' not in m:
        m['alignment'] = [ 'A' ]
    alignment.text = utils.convertAlignList(m['alignment'])

    ac = ET.SubElement(monster, 'ac')
    acstr = []
    for acs in m['ac']:
        if isinstance(acs, dict):
            if len(acstr) == 0:
                if 'ac' in acs:
                    acstr.append(str(acs['ac']))
                if 'from' in acs and 'condition' in acs:
                    acstr.append(utils.fixTags(", ".join(acs['from']) + " " + acs['condition'],m,True))
                elif 'from' in acs:
                    acstr.append(utils.fixTags(", ".join(acs['from']),m,True))
                elif 'condition' in acs:
                    acstr.append(utils.fixTags(acs['condition'],m,True))
                if 'special' in acs:
                    if re.search("^[0-9]+( [(].*[)])*$", acs['special']):
                        acstr.append(utils.fixTags(acs['special'],m,True))
                    else:
                        acstr.append('')
                continue
            acstr.append(utils.fixTags("{}".format(
                "{} {}".format(
                    acs['ac'],
                    "("+", ".join(acs['from']) + ") " + acs['condition'] if 'from' in acs and 'condition' in acs else
                    "("+", ".join(acs['from'])+")" if 'from' in acs else
                    acs['condition']
                    ) if 'from' in acs or 'condition' in acs else acs['ac']),m,True))
        else:
            acstr.append(str(acs))
    if len(acstr) > 1:
        ac.text = "{} ({})".format(acstr[0],", ".join(acstr[1:])) 
    elif acstr[0]:
        ac.text = acstr[0]
    else:
        ac.text = "0"

    hp = ET.SubElement(monster, 'hp')
    if "special" in m['hp']:
        if args.nohtml and re.match(r'equal the .*?\'s Constitution modifier',m['hp']['special']):
            hp.text = str(utils.getAbilityMod(m['con']))
            if 'trait' in m:
                m['trait'].insert(0,{"name": "Hit Points","entries": [ m['hp']['special'] ]})
            else:
                m['trait'] = [ {"name": "Hit Points","entries": [ m['hp']['special'] ]} ]
        elif args.nohtml:
            hpmatch = re.match(r'[0-9]+ ?(\([0-9]+[Dd][0-9]+( ?\+ ?[0-9]+)?\))?', m['hp']['special'])
            if hpmatch:
                hp.text = str(hpmatch.group(0)).rstrip()
            else:
                hp.text = "0"
            if 'trait' in m:
                m['trait'].insert(0,{"name": "Hit Points","entries": [ m['hp']['special'] ]})
            else:
                m['trait'] = [ {"name": "Hit Points","entries": [ m['hp']['special'] ]} ]
        else:
            hp.text = m['hp']['special']
    else:
        hp.text = "{} ({})".format(m['hp']['average'], m['hp']['formula'].replace(' ',''))

    speed = ET.SubElement(monster, 'speed')
    if type(m['speed']) == str:
        speed.text = m['speed']
    elif 'choose' in m['speed']:
        lis = []
        for key, value in m['speed'].items():
            if key == "walk":
                lis.append("walk " + str(value) + " ft.")
            elif key == "choose":
                value['from'].insert(-1, 'or')
                lis.append(
                    "{} {} ft. {}".format(
                        " ".join(
                            value['from']),
                        value['amount'],value['note']))
            else:
                lis.append("{} {} ft.".format(key, value))
        speed.text = ", ".join(lis)
    else:
        speed.text = ", ".join(
            [
                "{} {} ft.".format(
                    key,
                    value['number'] if isinstance(
                        value,
                        dict) else value) for key,
                value in m['speed'].items() if not isinstance(
                    value,
                    bool)])

    statstr = ET.SubElement(monster, 'str')
    statstr.text = str(m['str'] if 'str' in m else '0')
    statdex = ET.SubElement(monster, 'dex')
    statdex.text = str(m['dex'] if 'dex' in m else '0')
    statcon = ET.SubElement(monster, 'con')
    statcon.text = str(m['con'] if 'con' in m else '0')
    statint = ET.SubElement(monster, 'int')
    statint.text = str(m['int'] if 'int' in m else '0')
    statwis = ET.SubElement(monster, 'wis')
    statwis.text = str(m['wis'] if 'wis' in m else '0')
    statcha = ET.SubElement(monster, 'cha')
    statcha.text = str(m['cha'] if 'cha' in m else '0')
    if 'isNpc' in m and m['isNpc'] and not args.nohtml:
        npcroll = ET.SubElement(monster, 'role')
        npcroll.text = "ally"
    save = ET.SubElement(monster, 'save')
    if 'save' in m:
        saves = []
        for key, value in m['save'].items():
            if re.search("^[+-]?[0-9]+$", value, re.IGNORECASE):
                saves.append("{} {}".format(str.capitalize(key), value))
        save.text = ", ".join(saves)

    skill = ET.SubElement(monster, 'skill')
    if 'skill' in m:
        skills = []
        for key, value in m['skill'].items():
            if type(value) == str:
                skills.append("{} {}".format(str.capitalize(key), value))
            else:
                if key == "other":
                    for sk in value:
                        if "oneOf" in sk:
                            if args.nohtml:
                                if 'trait' not in m: m['trait'] = []
                                m['trait'].insert(0,{"name": "Skills","entries": [ "plus one of the following: "+", ".join(["{} {}".format(str.capitalize(ook), oov) for ook, oov in sk["oneOf"].items()]) ] })
                            else:
                                skills.append("plus one of the following: "+", ".join(["{} {}".format(str.capitalize(ook), oov) for ook, oov in sk["oneOf"].items()]))
        skill.text = ", ".join(skills)

    if 'passive' in m:
        passive = ET.SubElement(monster, 'passive')
        passive.text = str(m['passive'])

    languages = ET.SubElement(monster, 'languages')
    if 'languages' in m:
        languages.text = ", ".join([x for x in m['languages']])

    cr = ET.SubElement(monster, 'cr')
    if 'cr' in m:
        if isinstance(m['cr'], dict):
            cr.text = str(m['cr']['cr'])
        else:
            if not m['cr'] == "Unknown":
                cr.text = str(m['cr'])

    resist = ET.SubElement(monster, 'resist')
    if 'resist' in m:
        resistlist = utils.parseRIV(m, 'resist')
        resist.text = ", ".join(resistlist)

    immune = ET.SubElement(monster, 'immune')
    if 'immune' in m:
        immunelist = utils.parseRIV(m, 'immune')
        immune.text = ", ".join(immunelist)

    vulnerable = ET.SubElement(monster, 'vulnerable')
    if 'vulnerable' in m:
        vulnerablelist = utils.parseRIV(m, 'vulnerable')
        vulnerable.text = ", ".join(vulnerablelist)

    conditionImmune = ET.SubElement(monster, 'conditionImmune')
    if 'conditionImmune' in m:
        conditionImmunelist = utils.parseRIV(m, 'conditionImmune')
        conditionImmune.text = ", ".join(conditionImmunelist)

    senses = ET.SubElement(monster, 'senses')
    if 'senses' in m:
        senses.text = ", ".join([x for x in m['senses']])

    if 'source' in m and not args.srd:
        slug = slugify(m["name"])
        if args.addimgs and os.path.isdir("img") and not os.path.isfile(os.path.join(args.tempdir,"monsters", slug + ".png")) and not os.path.isfile(os.path.join(args.tempdir,"monsters",slug+".jpg")) and not os.path.isfile(os.path.join(args.tempdir,"monsters", "token_" + slug + ".png")) and not os.path.isfile(os.path.join(args.tempdir,"monsters", "token_" + slug + ".jpg")):
            if not os.path.isdir(os.path.join(args.tempdir,"monsters")):
                os.mkdir(os.path.join(args.tempdir,"monsters"))
            #if not os.path.isdir(os.path.join(args.tempdir,"tokens")):
            #    os.mkdir(os.path.join(args.tempdir,"tokens"))
            if 'image' in m:
                artworkpath = m['image']
            else:
                artworkpath = None
            monstername = m["original_name"] if "original_name" in m else m["name"]
            if artworkpath and os.path.isfile("./img/" + artworkpath):
                artworkpath = "./img/" + artworkpath
            elif os.path.isfile("./img/bestiary/" + m["source"] + "/" + monstername + ".jpg"):
                artworkpath = "./img/bestiary/" + m["source"] + "/" + monstername + ".jpg"
            elif os.path.isfile("./img/bestiary/" + m["source"] + "/" + monstername + ".png"):
                artworkpath = "./img/bestiary/" + m["source"] + "/" + monstername + ".png"
            elif os.path.isfile("./img/vehicles/" + m["source"] + "/" + monstername + ".jpg"):
                artworkpath = "./img/vehicles/" + m["source"] + "/" + monstername + ".jpg"
            elif os.path.isfile("./img/vehicles/" + m["source"] + "/" + monstername + ".png"):
                artworkpath = "./img/vehicles/" + m["source"] + "/" + monstername + ".png"
            if artworkpath is not None:
                ext = os.path.splitext(artworkpath)[1]
                copyfile(artworkpath, os.path.join(args.tempdir,"monsters",slug + ext))
                imagetag = ET.SubElement(monster, 'image')
                imagetag.text = slug + ext
            if os.path.isfile("./img/" + m["source"] + "/" + monstername + ".png") or os.path.isfile("./img/" + m["source"] + "/" + monstername + ".jpg"):
                if os.path.isfile("./img/" + m["source"] + "/" + monstername + ".png"):
                    artworkpath = "./img/" + m["source"] + "/" + monstername + ".png"
                else:
                    artworkpath = "./img/" + m["source"] + "/" + monstername + ".jpg"
                ext = os.path.splitext(artworkpath)[1]
                copyfile(artworkpath, os.path.join(args.tempdir,"monsters","token_" + slug + ext))
                imagetag = ET.SubElement(monster, 'token')
                imagetag.text = slug + ext
            elif os.path.isfile("./img/vehicles/tokens/" + m["source"] + "/" + monstername + ".png") or os.path.isfile("./img/vehicles/tokens/" + m["source"] + "/" + monstername + ".jpg"):
                if os.path.isfile("./img/vehicles/tokens/" + m["source"] + "/" + monstername + ".png"):
                    artworkpath = "./img/vehicles/tokens/" + m["source"] + "/" + monstername + ".png"
                else:
                    artworkpath = "./img/vehicles/tokens/" + m["source"] + "/" + monstername + ".jpg"
                ext = os.path.splitext(artworkpath)[1]
                copyfile(artworkpath, os.path.join(args.tempdir,"monsters","token_" + slug + ext))
                imagetag = ET.SubElement(monster, 'token')
                imagetag.text = "token_" + slug + ext
        elif args.addimgs and os.path.isfile(os.path.join(args.tempdir,"monsters", slug + ".png")):
            imagetag = ET.SubElement(monster, 'image')
            imagetag.text = slug + ".png"
        elif args.addimgs and os.path.isfile(os.path.join(args.tempdir,"monsters", slug + ".jpg")):
            imagetag = ET.SubElement(monster, 'image')
            imagetag.text = slug + ".jpg"
        elif args.addimgs and os.path.isfile(os.path.join(args.tempdir,"monsters", "token_" + slug + ".png")):
            imagetag = ET.SubElement(monster, 'token')
            imagetag.text = "token_" + slug + ".png"
        elif args.addimgs and os.path.isfile(os.path.join(args.tempdir,"monsters", "token_" + slug + ".jpg")):
            imagetag = ET.SubElement(monster, 'token')
            imagetag.text = "token_" + slug + ".jpg"
        sourcetext = "{} p. {}".format(
            utils.getFriendlySource(m['source']), m['page']) if 'page' in m and m['page'] != 0 else utils.getFriendlySource(m['source'])

        if 'otherSources' in m and m["otherSources"] is not None:
            for s in m["otherSources"]:
                if "source" not in s:
                    continue
                sourcetext += ", "
                sourcetext += "{} p. {}".format(
                    utils.getFriendlySource(s["source"]), s["page"]) if 'page' in s and s["page"] != 0 else utils.getFriendlySource(s["source"])
        #trait = ET.SubElement(monster, 'trait')
        #name = ET.SubElement(trait, 'name')
        #name.text = "Source"
        #text = ET.SubElement(trait, 'text')
        #text.text = sourcetext
        if not args.nohtml:
            srctag = ET.SubElement(monster, 'source')
            srctag.text = sourcetext
    else:
        sourcetext = None


    if 'trait' in m:
        for t in m['trait']:
            trait = ET.SubElement(monster, 'trait')
            name = ET.SubElement(trait, 'name')
            name.text = utils.remove5eShit(t['name'])
            for e in utils.getEntryString(t["entries"],m,args).split("\n"):
                text = ET.SubElement(trait, 'text')
                text.text = e

    if 'action' in m and m['action'] is not None:
        for t in m['action']:
            action = ET.SubElement(monster, 'action')
            if 'name' in t:
                name = ET.SubElement(action, 'name')
                name.text = utils.remove5eShit(t['name'])
            for e in utils.getEntryString(t["entries"],m,args).split("\n"):
                text = ET.SubElement(action, 'text')
                text.text = e
                for match in re.finditer(r'(((\+|\-)?[0-9]*) to hit.*?|DC [0-9]+ .*? saving throw.*?)\(([0-9Dd\+\- ]+)\) .*? damage',e):
                    if match.group(4):
                        attack = ET.SubElement(action, 'attack')
                        attack.text = "{}|{}|{}".format(utils.remove5eShit(t['name']) if 'name' in t else "",match.group(2).replace(' ','') if match.group(2) else "",match.group(4).replace(' ',''))


    if 'reaction' in m and m['reaction'] is not None:
        for t in m['reaction']:
            action = ET.SubElement(monster, 'reaction')
            name = ET.SubElement(action, 'name')
            name.text = utils.remove5eShit(t['name'])
            for e in utils.getEntryString(t["entries"],m,args).split("\n"):
                text = ET.SubElement(action, 'text')
                text.text = e

    if 'variant' in m and m['variant'] is not None:
        for t in m['variant']:
            action = ET.SubElement(monster, 'action')
            name = ET.SubElement(action, 'name')
            name.text = "Variant: " + utils.remove5eShit(t['name'])
            for e in utils.getEntryString(t["entries"],m,args).split("\n"):
                text = ET.SubElement(action, 'text')
                text.text = e

    if 'legendary' in m:
        legendary = ET.SubElement(monster, 'legendary')

        if "legendaryHeader" in m:
            for h in m['legendaryHeader']:
                text = ET.SubElement(legendary, 'text')
                text.text = utils.remove5eShit(h)
        else:
            text = ET.SubElement(legendary, 'text')
            if "isNamedCreature" in m and m['isNamedCreature']:
                text.text = "{0} can take {1:d} legendary action{2}, choosing from the options below. Only one legendary action can be used at a time and only at the end of another creature's turn. {0} regains spent legendary action{2} at the start of its turn.".format(m['name'].split(' ', 1)[0],len(m['legendary']),"s" if len(m['legendary']) > 1 else "")
            else:
                text.text = "The {0} can take {1:d} legendary action{2}, choosing from the options below. Only one legendary action can be used at a time and only at the end of another creature's turn. The {0} regains spent legendary action{2} at the start of its turn.".format(m['type'] if type(m['type']) == str else "{} ({})".format(m['type']['type'],", ".join(m['type']['tags'])) if 'tags' in m['type'] else m['type']['type'],len(m['legendary']),"s" if len(m['legendary']) > 1 else "")
        for t in m['legendary']:
            legendary = ET.SubElement(monster, 'legendary')
            name = ET.SubElement(legendary, 'name')
            if 'name' not in t:
                t['name'] = ""
            name.text = utils.remove5eShit(t['name'])
            for e in utils.getEntryString(t["entries"],m,args).split("\n"):
                text = ET.SubElement(legendary, 'text')
                text.text = e

    if 'mythic' in m:
        mythic = ET.SubElement(monster, 'legendary')

        if "mythicHeader" in m:
            for h in m['mythicHeader']:
                name = ET.SubElement(mythic, 'name')
                name.text = "Mythic Actions"
                mythic = ET.SubElement(monster, 'legendary')
                text = ET.SubElement(mythic, 'text')
                text.text = utils.remove5eShit(h)
        for t in m['mythic']:
            mythic = ET.SubElement(monster, 'legendary')
            name = ET.SubElement(mythic, 'name')
            if 'name' not in t:
                t['name'] = ""
            name.text = utils.remove5eShit(t['name'])
            for e in utils.getEntryString(t["entries"],m,args).split("\n"):
                text = ET.SubElement(mythic, "text")
                text.text = e

    if 'legendaryGroup' in m:
        with open("./data/bestiary/legendarygroups.json",encoding='utf-8') as f:
            meta = json.load(f)
            f.close()
        for l in meta['legendaryGroup']:
            if l['name'] != m['legendaryGroup']['name']:
                continue
            if 'lairActions' in l:
                legendary = ET.SubElement(monster, 'legendary')
                name = ET.SubElement(legendary, 'name')
                name.text = "Lair Actions"
                legendary = ET.SubElement(monster, 'legendary')
                for t in l['lairActions']:
                    if type(t) == str:
                        text = ET.SubElement(legendary, 'text')
                        text.text = utils.fixTags(t,m,args.nohtml)
                        continue
                    if 'name' in t:
                        name = ET.SubElement(legendary, 'name')
                        name.text = "Lair Action: " + utils.remove5eShit(t['name'])
                    if t['type'] == 'list':
                        for i in t['items']:
                            text = ET.SubElement(legendary, 'text')
                            text.text = "• " + utils.fixTags(i,m,args.nohtml)
                        continue
                    for e in utils.getEntryString(t["entries"],m,args).split("\n"):
                        text = ET.SubElement(legendary, 'text')
                        text.text = e

            if 'regionalEffects' in l:
                legendary = ET.SubElement(monster, 'legendary')
                name = ET.SubElement(legendary, 'name')
                name.text = "Regional Effects"
                legendary = ET.SubElement(monster, 'legendary')
                for t in l['regionalEffects']:
                    if type(t) == str:
                        text = ET.SubElement(legendary, 'text')
                        text.text = utils.fixTags(t,m,args.nohtml)
                        continue
                    if 'name' in t:
                        name = ET.SubElement(legendary, 'name')
                        name.text = "Regional Effect: " + utils.remove5eShit(t['name'])
                    if t['type'] == 'list':
                        for i in t['items']:
                            text = ET.SubElement(legendary, 'text')
                            text.text = "• " + utils.fixTags(i,m,args.nohtml)
                        continue
                    #legendary = ET.SubElement(monster, 'legendary')
                    for e in utils.getEntryString(t["entries"],m,args).split("\n"):
                        text = ET.SubElement(legendary, 'text')
                        text.text = e
            if 'mythicEncounter' in l:
                mythic = ET.SubElement(monster, 'legendary')
                name = ET.SubElement(mythic, 'name')
                name.text = "{} as a Mythic Encounter".format(m["name"])
                for e in utils.getEntryString(l["mythicEncounter"],m,args).split("\n"):
                    text = ET.SubElement(mythic, 'text')
                    text.text = e



    if 'spellcasting' in m:
        spells = []
        for s in m['spellcasting']:
            trait = ET.SubElement(monster, 'trait')
            name = ET.SubElement(trait, 'name')
            name.text = utils.remove5eShit(s['name'])
            for e in s['headerEntries']:
                text = ET.SubElement(trait, 'text')
                text.text = utils.fixTags(e,m,args.nohtml)

            if "will" in s:
                text = ET.SubElement(trait, 'text')
                willspells = s['will']
                text.text = "At will: " + \
                    ", ".join([utils.remove5eShit(e) for e in willspells])
                for spl in willspells:
                    search = re.search(
                        r'{@spell+ (.*?)(\|.*)?}', spl, re.IGNORECASE)
                    if search is not None:
                        spells.append(search.group(1))

            if "daily" in s:
                for timeframe, lis in s['daily'].items():
                    text = ET.SubElement(trait, 'text')
                    dailyspells = lis
                    t = "{}/day{}: ".format(timeframe[0],
                                            " each" if len(timeframe) > 1 else "")
                    text.text = t + \
                        ", ".join([utils.fixTags(e,m,args.nohtml) for e in dailyspells])
                    for spl in dailyspells:
                        search = re.search(
                            r'{@spell+ (.*?)(\|.*)?}', spl, re.IGNORECASE)
                        if search is not None:
                            spells.append(search.group(1))

            if "spells" in s:
                slots = []
                for level, obj in s['spells'].items():
                    text = ET.SubElement(trait, 'text')
                    spellbois = obj['spells']
                    t = "• {} level ({} slots): ".format(
                        utils.ordinal(
                            int(level)),
                        obj['slots'] if 'slots' in obj else 0) if level != "0" else "Cantrips (at will): "
                    if level != "0":
                        slots.append(
                            str(obj['slots'] if 'slots' in obj else 0))
                    text.text = t + \
                        ", ".join([utils.fixTags(e,m,args.nohtml) for e in spellbois])
                    for spl in spellbois:
                        search = re.search(
                            r'{@spell+ (.*?)(\|.*)?}', spl, re.IGNORECASE)
                        if search is not None:
                            spells.append(search.group(1))
                slotse = ET.SubElement(monster, 'slots')
                slotse.text = ", ".join(slots)
            if 'footerEntries' in s:
                for e in s['footerEntries']:
                    text = ET.SubElement(trait, 'text')
                    text.text = utils.fixTags(e,m,args.nohtml)

        spellse = ET.SubElement(monster, 'spells')
        spellse.text = ", ".join(spells)

    description = ET.SubElement(monster, 'description')
    description.text = ""
    if 'entries' in m and not args.srd:
        description.text += utils.getEntryString(m["entries"],m,args)

    if sourcetext: description.text += "\n<i>Source: {}</i>".format(sourcetext)
    if args.nohtml:
        description.text = re.sub('</?(i|b|spell)>', '', description.text)
    environment = ET.SubElement(monster, 'environment')
    if 'environment' in m:
        environment.text = ", ".join([x for x in m['environment']])
    # print(m['name'])

# vim: set tabstop=8 softtabstop=0 expandtab shiftwidth=4 smarttab : #
import xml.etree.cElementTree as ET
import re
import utils
import json
import os
from slugify import slugify
from wand.image import Image

def parseClass(m, compendium, args):
#    for eachClasss in compendium.findall('Class'):
#        if eachClasss.find('name').text == m['name']:
#            m['name'] = "{} (DUPLICATE IN {})".format(m['name'],m['source'])
    stats = {"str":"Strength","dex":"Dexterity","con":"Constitution","int":"Intelligence","wis":"Wisdom","cha":"Charisma"}
    slots=""
    numberofSkills=""
    if 'hd' not in m:
        m['hd'] = { "number": 1, "faces": 10 }
    if 'startingProficiencies' not in m:
        m["startingProficiencies"] = {}
    if 'skills' not in m['startingProficiencies']:
        m['startingProficiencies']['skills'] = []
    Class = ET.SubElement(compendium, 'class')
    name = ET.SubElement(Class, 'name')
    name.text = m['name']
    if not args.onlyofficial or \
        ('source' in m and m['source'] in args.onlyofficial):
        hd = ET.SubElement(Class, 'hd')
        hd.text = str(m['hd']['faces'])
        saveProficiency = []
        for stat, value in stats.items():
            if 'proficiency' in m and stat in m['proficiency']:
                saveProficiency.append("{}".format(stats[stat]))
        proficiency = ET.SubElement(Class, 'proficiency')
        proficiencyList = []
        numSkills = ET.SubElement(Class, 'numSkills')
        for skill in m['startingProficiencies']['skills']:
            if 'choose' in skill and 'from' in skill['choose']:
                skillList = skill['choose']['from']
                proficiencyList = saveProficiency + skillList
                proficiencytext = ", ".join(proficiencyList).title()
                proficiency.text = proficiencytext
                numberofSkills = str(skill['choose']['count'])
                numSkills.text = str(skill['choose']['count'])
        
        spellcastingAbility = ""
        if 'spellcastingAbility' in m:
            spellAbility = ET.SubElement(Class, 'spellAbility')
            spellcastingAbility = "{}".format(stats[m['spellcastingAbility']])
            spellAbility.text = spellcastingAbility
        myattributes = {"level":"1"}
        autolevel = ET.SubElement(Class, 'autolevel', myattributes)
        featureattributes={"optional": "YES"}
        StartingFeature = ET.SubElement(autolevel, 'feature',featureattributes)
        SFName = ET.SubElement(StartingFeature, 'name')
        SFName.text = "Starting " + m['name']
        SFText = ET.SubElement(StartingFeature, 'text')
        SFText.text = "As a 1st-level " + m['name'] + ", you begin play with " + str(
            m['hd']['faces']) + "+your Constitution modifier hit points."
        SFText = ET.SubElement(StartingFeature, 'text')
        SFText.text = ""
        SFText = ET.SubElement(StartingFeature, 'text')
        SFText.text = "You are proficient with the following items, in addition to any proficiencies provided by your race or background."
        SFText = ET.SubElement(StartingFeature, 'text')
        if "armor" in m['startingProficiencies']:
            armortext = ", ".join([x if type(x) == str else x['full'] for x in m['startingProficiencies']['armor']])
        else:
            armortext = "none"
        SFText.text = "• Armor: " + armortext
        SFText = ET.SubElement(StartingFeature, 'text')
        if "weapons" in m['startingProficiencies']:
            weapontext = ", ".join(m['startingProficiencies']['weapons'])
        else:
            weapontext = "none"
        SFText.text = "• Weapons: " + weapontext
        SFText = ET.SubElement(StartingFeature, 'text')
        if "tools" in m['startingProficiencies']:
            SFText.text = utils.fixTags("• Tools: " + ", ".join(m['startingProficiencies']['tools']),m,args.nohtml)
        else:
            SFText.text = "• Tools: none"
        SFText = ET.SubElement(StartingFeature, 'text')
        if numberofSkills != "":
            SFText.text = "• Skills: Choose " + numberofSkills + " from " + ", ".join(skillList).title()
            SFText = ET.SubElement(StartingFeature, 'text')
            SFText.text = ""
        SFText = ET.SubElement(StartingFeature, 'text')
        if 'startingEquipment' in m:
            SFText.text = "You begin play with the following equipment, in addition to any equipment provided by your background."
            for startingEquipment in m['startingEquipment']['default']:
                SFText = ET.SubElement(StartingFeature, 'text')
                SFText.text = "• " + utils.fixTags(startingEquipment,m,args.nohtml)
            SFText = ET.SubElement(StartingFeature, 'text')
            SFText.text = ""
            if "goldAlternative" in m['startingEquipment']:
                SFText = ET.SubElement(StartingFeature, 'text')
                SFText.text = "Alternatively, you may start with " + utils.fixTags(
                    m['startingEquipment']['goldAlternative'],m,args.nohtml) + " gp and choose your own equipment."
                SFText = ET.SubElement(StartingFeature, 'text')
                SFText.text = ""
        if not args.srd:
            SFText = ET.SubElement(StartingFeature, 'text')
            if 'page' in m:
                SFText.text = "Source: " + utils.getFriendlySource(m['source'],args) + " p. " + str(m['page'])
            else:
                SFText.text = "Source: " + utils.getFriendlySource(m['source'],args)
        if 'multiclassing' in m:
            myattributes = {"level":"1"}
            autolevel = ET.SubElement(Class, 'autolevel', myattributes)
            featureattributes={"optional": "YES"}
            StartingFeature = ET.SubElement(autolevel, 'feature',featureattributes)
            SFName = ET.SubElement(StartingFeature, 'name')
            SFName.text = "Multiclass " + m['name']
            SFText = ET.SubElement(StartingFeature, 'text')
            SFText.text = 'To multiclass as a ' + m['name'] + ', you must meet the following prerequisites:'
            SFText = ET.SubElement(StartingFeature, 'text')
            if 'or' in m['multiclassing']['requirements']:
                MCrequirements={}
                for requirement, value in m['multiclassing']['requirements']['or'][0].items():
                    MCrequirements[str(requirement)]=str(value)
                    SFText = ET.SubElement(StartingFeature, 'text')
                    SFText.text= "• {} {}".format(stats[requirement],MCrequirements[requirement])
            else:
                for requirement, value in m['multiclassing']['requirements'].items():
                    SFText.text = "• {} {}".format(stats[requirement],m['multiclassing']['requirements'][requirement])
            SFText = ET.SubElement(StartingFeature, 'text')
            SFText.text = ""
            if 'proficienciesGained' in m['multiclassing'] or 'tools' in m['multiclassing']:
                SFText = ET.SubElement(StartingFeature, 'text')
                SFText.text = "You gain the following proficiencies:"
                if 'proficienciesGained' in m['multiclassing']:
                    SFText = ET.SubElement(StartingFeature, 'text')
                    if "armor" in m['multiclassing']['proficienciesGained']:
                        MCarmortext = ", ".join([x if type(x) == str else x['full'] for x in m['multiclassing']['proficienciesGained']['armor']])
                    else:
                        MCarmortext = "none"
                    SFText.text = "• Armor: " + MCarmortext
                    SFText = ET.SubElement(StartingFeature, 'text')
                    if "weapons" in m['multiclassing']['proficienciesGained']:
                        MCweapontext = ", ".join(m['multiclassing']['proficienciesGained']['weapons'])
                    else:
                        MCweapontext = "none"
                        SFText.text = "• Weapons: " + MCweapontext
                SFText = ET.SubElement(StartingFeature, 'text')
                if "tools" in m['multiclassing']:
                    MCtooltext = utils.fixTags(", ".join(m['multiclassing']['tools']),m,args.nohtml)
                else:
                    MCtooltext = "none"
                SFText.text = "• Tools: " + MCtooltext
                SFText = ET.SubElement(StartingFeature, 'text')
                SFText.text = ""
            if not args.srd:
                SFText = ET.SubElement(StartingFeature, 'text')
                if 'page' in m:
                    SFText.text = "Source: " + utils.getFriendlySource(m['source'],args) + " p. " + str(m['page'])
                else:
                    SFText.text = "Source: " + utils.getFriendlySource(m['source'],args)
        armor = ET.SubElement(Class, 'armor')
        armor.text = armortext
        weapons = ET.SubElement(Class, 'weapons')
        weapons.text = weapontext
        tools = ET.SubElement(Class, 'tools')
        if "tools" in m['startingProficiencies']:
            tools.text = utils.fixTags(", ".join(m['startingProficiencies']['tools']),m,args.nohtml)
        else:
            tools.text = "none"
        if 'startingEquipment' in m and "goldAlternative" in m['startingEquipment']:
            wealth = ET.SubElement(Class, 'wealth')
            wealth.text = utils.fixTags(m['startingEquipment']['goldAlternative'],m,args.nohtml).replace(" ", "")
        if 'casterProgression' in m:
            FullCaster =[[3,2,0,0,0,0,0,0,0,0],[3,3,0,0,0,0,0,0,0,0],[3,4,2,0,0,0,0,0,0,0],[4,4,3,0,0,0,0,0,0,0],[4,4,3,2,0,0,0,0,0,0],[4,4,3,3,0,0,0,0,0,0],[4,4,3,3,1,0,0,0,0,0],[4,4,3,3,2,0,0,0,0,0],[4,4,3,3,3,1,0,0,0,0],[5,4,3,3,3,2,0,0,0,0],[5,4,3,3,3,2,1,0,0,0],[5,4,3,3,3,2,1,0,0,0],[5,4,3,3,3,2,1,1,0,0],[5,4,3,3,3,2,1,1,0,0],[5,4,3,3,3,2,1,1,1,0],[5,4,3,3,3,2,1,1,1,0],[5,4,3,3,3,2,1,1,1,1],[5,4,3,3,3,3,1,1,1,1],[5,4,3,3,3,3,2,1,1,1],[5,4,3,3,3,3,2,2,1,1]]
            HalfCaster =[[0,0,0,0,0,0],[0,2,0,0,0,0],[0,3,0,0,0,0],[0,3,0,0,0,0],[0,4,2,0,0,0],[0,4,2,0,0,0],[0,4,3,0,0,0],[0,4,3,0,0,0],[0,4,3,2,0,0],[0,4,3,2,0,0],[0,4,3,3,0,0],[0,4,3,3,0,0],[0,4,3,3,1,0],[0,4,3,3,1,0],[0,4,3,3,2,0],[0,4,3,3,2,0],[0,4,3,3,3,1],[0,4,3,3,3,1],[0,4,3,3,3,2],[0,4,3,3,3,2]]
            ThirdCaster =[[0,0,0,0,0],[0,0,0,0,0],[0,2,0,0,0],[0,3,0,0,0],[0,3,0,0,0],[0,3,0,0,0],[0,4,2,0,0],[0,4,2,0,0],[0,4,2,0,0],[0,4,3,0,0],[0,4,3,0,0],[0,4,3,0,0],[0,4,3,2,0],[0,4,3,2,0],[0,4,3,2,0],[0,4,3,3,0],[0,4,3,3,0],[0,4,3,3,0],[0,4,3,3,1],[0,4,3,3,1]]
            #if 'Cantrips Known' in m['classTableGroups'][0]["colLabels"]:
            #    print(m['classTableGroups'][0]["colLabels"][0])
            #    print(type(m['classTableGroups'][0]["colLabels"][0]))
            #    print("Cantrips are known")
            if m['casterProgression']== 'full':
                slots=FullCaster
            elif m['casterProgression']== '1/2':
                slots=HalfCaster
            elif m['casterProgression']== '1/3':
                slots=ThirdCaster
            else:
                slots=[[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
            for table in m['classTableGroups']:
                if "title" in table and table['title'] == "Spell Slots per Spell Level":
                    for lvl in range(len(table["rows"])):
                        for c in table["rows"][lvl]:
                            slots[lvl] = table["rows"][lvl]
            for table in m['classTableGroups']:
                cantripre = re.compile(r'{@filter ([Cc]antrips.*?)(\|.*?)?(\|.*?)?}')
                for i in range(len(table["colLabels"])):
                    if cantripre.match(table["colLabels"][i]):
                        cantrips = True
                        for lvl in range(len(table["rows"])):
                            slots[lvl].insert(0,table["rows"][lvl][i])
                        break
            try:
                cantrips
            except NameError:
                for lvl in range(len(slots)):
                    slots[lvl].insert(0,0)
            for levelcounter in range(len(slots)):
                while slots[levelcounter] and slots[levelcounter][-1] == 0:
                    slots[levelcounter].pop()
    level = 0
    currentsubclass = 0
    currentsubclassFeature = 0
    for level in range(20):
        if slots:
            if level<20 and slots[level]:
                attributes = {"level": str(level+1)}
                autolevel = ET.SubElement(Class, 'autolevel', attributes)
                spellslots = ET.SubElement(autolevel, 'slots')
                currentspellevel = level
                spellslots.text = ", ".join(str(e) for e in slots[currentspellevel])
        for featureRef in m['classFeatures']:
            feature = {}
#classFeature UID
#<name>|<className>|<classSource>|<level>|<source>
#subclassFeature UID
#0       1           2               3                   4               5       6
#<name>|<className>|<classSource>|<subclassShortName>|<subclassSource>|<level>|<source>
            for cf in m["classFeature"]:
                if type(featureRef) == str:
                    featureRefs = featureRef.split('|')
                else:
                    featureRefs = featureRef["classFeature"].split('|')
                if cf["name"] == featureRefs[0] and cf["className"] == featureRefs[1] and int(featureRefs[3]) == cf["level"] and \
                (cf["classSource"] == featureRefs[2] or (featureRefs[2] == "" and cf["classSource"] == m["source"])) and \
                (len(featureRefs) == 4 or cf["source"] == featureRefs[4]):
                    feature = cf
                    break
            if not feature or feature['level'] != (level+1):
                continue
            if 'name' in feature and feature['name'] == "Ability Score Improvement":
                attributes = {"level": str(level+1),"scoreImprovement":"YES"}
            else:
                attributes = {"level": str(level+1)}
            if type(featureRef) != dict or "gainSubclassFeature" not in featureRef or featureRef["gainSubclassFeature"] == False:
                if args.srd:
                    if 'srd' not in feature or not feature['srd']:
                        if "gainSubclassFeature" in feature and feature["gainSubclassFeature"]==True:
                            currentsubclassFeature += 1
                        continue
                if args.skipua and 'source' in feature and feature['source'].startswith('UA'):
                    if args.verbose:
                        print("Skipping UA Feature:",m['name'],feature['name'])
                    if type(featureRef) == dict and "gainSubclassFeature" in featureRef and featureRef["gainSubclassFeature"]==True:
                        currentsubclassFeature += 1
                    continue
                if args.onlyofficial and \
                    m['source'] not in ['UAModifyingClasses', 'UARanger', 'UATheRangerRevised']:
                    if 'source' in feature and feature['source'] not in args.onlyofficial and \
                        not hasSubfeatureInSource(feature, args):
                        if args.verbose:
                            print("Skipping unoffical content: {} from {}".format(feature['name'],utils.getFriendlySource(feature['source'],args)))
                        if type(featureRef) == dict and "gainSubclassFeature" in featureRef and featureRef["gainSubclassFeature"]==True:
                            currentsubclassFeature += 1
                        continue
            # Check if subfeature is in the source
            if not args.onlyofficial or \
                ('source' in feature and feature['source'] in args.onlyofficial) or \
                hasSubfeatureInSource(feature, args) or \
                m['source'] in ['UAModifyingClasses', 'UARanger', 'UATheRangerRevised']:
                
                autolevel = ET.SubElement(Class, 'autolevel', attributes)
                attributes = {}
                
                if not args.onlyofficial or (args.onlyofficial and feature['source'] in args.onlyofficial):
                    ft = ET.SubElement(autolevel, 'feature',attributes)
                    ftname = ET.SubElement(ft,'name')
                    ftname.text = utils.fixTags(feature["name"],m,args.nohtml)
                
                for subfeature in feature['entries']:
                    if type(subfeature) == dict and 'type' in subfeature and subfeature['type'] == 'options':
                        for opt in subfeature['entries']:
                            if opt["type"] == "refOptionalfeature":
                                optRef = opt["optionalfeature"].split('|')
                                with open("./data/optionalfeatures.json",encoding='utf-8') as f:
                                    meta = json.load(f)
                                    f.close()
                                for of in meta["optionalfeature"]:
                                    if of["name"] == optRef[0] and (len(optRef) == 1 or of["source"] == optRef[1]):
                                        opt["name"] = of["name"]
                                        opt["entries"] = of["entries"]
                                        opt["source"] = of["source"]
                                        if 'page' in cf:
                                            opt["page"] = cf ["page"]
                                        break
                            elif opt["type"] == "refClassFeature":
                                optRef = opt["classFeature"].split('|')
                                for cf in m["classFeature"]:
                                    if cf["name"] == optRef[0] and cf["className"] == optRef[1] and int(optRef[3]) == cf["level"] and \
                                    (cf["classSource"] == optRef[2] or (optRef[2] == "" and cf["classSource"] == m["source"])) and \
                                    (len(optRef) == 4 or cf["source"] == optRef[4]):
                                        opt["name"] = cf["name"]
                                        opt["entries"] = cf["entries"]
                                        opt["source"] = cf["source"]
                                        if 'page' in cf:
                                            opt["page"] = cf ["page"]
                                        break
                            if args.srd:
                                if 'srd' not in opt or not opt['srd']:
                                    continue
                            if args.skipua and 'source' in opt and opt['source'].startswith('UA'):
                                if args.verbose:
                                    print("Skipping UA Feature:",m['name'],opt['name'])
                                continue
                            if args.onlyofficial and \
                                m['source'] not in ['UAModifyingClasses', 'UARanger', 'UATheRangerRevised']:
                                if 'source' in opt and opt['source'] not in args.onlyofficial:
                                    if args.verbose:
                                        print("Skipping unoffical content: {} from {}".format(opt['name'],utils.getFriendlySource(opt['source'],args)))
                                    continue
                            sfopt = ET.SubElement(autolevel,'feature',{"optional": "YES"})
                            sfoptname = ET.SubElement(sfopt,'name')
                            sfoptname.text = "{}: {}".format(utils.fixTags(feature["name"],m,args.nohtml),utils.fixTags(opt["name"],m,args.nohtml))
                            flatten_json(opt['entries'],m,sfopt,args, level,attributes)
                            if not args.srd:
                                SFText = ET.SubElement(sfopt, 'text')
                                SFText.text = ""
                                SFText = ET.SubElement(sfopt, 'text')
                                if 'page' in opt:
                                    SFText.text = "Source: " + utils.getFriendlySource(opt['source'],args) + " p. " + str(opt['page'])
                                else:
                                    SFText.text = "Source: " + utils.getFriendlySource(opt['source'],args)
                    elif not args.onlyofficial or (args.onlyofficial and feature['source'] in args.onlyofficial):
                        flatten_json(subfeature,m,ft,args, level,attributes)
                if not args.srd and \
                    not args.onlyofficial or (args.onlyofficial and feature['source'] in args.onlyofficial):
                    SFText = ET.SubElement(ft, 'text')
                    SFText.text = ""
                    SFText = ET.SubElement(ft, 'text')
                    if 'page' in feature:
                        SFText.text = "Source: " + utils.getFriendlySource(feature['source'],args) + " p. " + str(feature['page'])
                    else:
                        SFText.text = "Source: " + utils.getFriendlySource(feature['source'],args)
            if type(featureRef) == dict and "gainSubclassFeature" in featureRef and featureRef["gainSubclassFeature"]==True:
                currentsubclass=0
                if 'subclasses' not in m:
                    continue
                for subclass in m['subclasses']:
                    if args.srd:
                        if 'srd' not in subclass or not subclass['srd']:
                            currentsubclass += 1
                            continue
                    if args.skipua and 'source' in subclass and subclass['source'].startswith('UA'):
                        if args.verbose:
                            print("Skipping UA Subclass:",m['name'],subclass['name'])
                        currentsubclass += 1
                        continue
                    if args.onlyofficial and \
                        m['source'] not in ['UAModifyingClasses', 'UARanger', 'UATheRangerRevised']:
                        if 'source' in subclass and subclass['source'] not in args.onlyofficial:
                            if args.verbose:
                                print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                            currentsubclass += 1
                            continue
                    subclassname=subclass['name']
                    #ft = ET.SubElement(autolevel, 'feature',attributes)
                    #print(subclass['source'])
                    #if currentsubclassFeature == 0:
                    #    ftname = ET.SubElement(ft,'name')
                    #    ftname.text = "{}: {}".format(utils.fixTags(m['subclassTitle'],m,args.nohtml),subclassname)
                    for subfeature in m['subclassFeature']:
                        if subfeature['level'] != (level+1) or subfeature['subclassShortName'] != subclass['shortName']:
                            continue
                        if args.onlyofficial and \
                            "isClassFeatureVariant" in subfeature and subfeature['isClassFeatureVariant'] and \
                            subfeature['source'] not in args.onlyofficial:
                            continue
                        attributes = {"level": str(level+1)}
                        autolevel = ET.SubElement(Class, 'autolevel', attributes)
                        attributes = {"optional": "YES"}

                        ft = ET.SubElement(autolevel, 'feature',attributes)
                        ftname = ET.SubElement(ft,'name')
                        if subclassname == subfeature['name']:
                            ftname.text = "{}: {}".format(utils.fixTags(m['subclassTitle'],m,args.nohtml),subfeature['name'])
                        else:
                            ftname.text = "{}: {}".format(utils.fixTags(subclassname,m,args.nohtml),subfeature['name'])

                        if 'entries' in subfeature:
                            for entry in subfeature['entries']:
                                if type(entry) is str:
                                    fttext = ET.SubElement(ft,'text')
                                    fttext.text = utils.fixTags(entry,m,args.nohtml)
                                else:
                                    if currentsubclassFeature == 0:
                                        flatten_json(entry,m,ft,args, level, attributes)
                                    else:
                                        flatten_json(entry,m,ft,args, level, attributes,subclassname)
                        else:
                            print("this shouldn't happen")
                        if not args.srd:
                            SFText = ET.SubElement(ft, 'text')
                            SFText.text = ""
                            SFText = ET.SubElement(ft, 'text')
                            if 'page' in subclass:
                                SFText.text = "Source: " + utils.getFriendlySource(subclass['source'],args) + " p. " + str(subclass['page'])
                            else:
                                SFText.text = "Source: " + utils.getFriendlySource(subclass['source'],args)
                        currentsubclass += 1
                    currentsubclassFeature += 1

def flatten_json(nested_json, d, Class, args, level, attributes,subclassname=''):
    def flatten(x, m, args, name=''):
        if args.srd:
            if 'srd' not in m or not m['srd']:
                return
        if args.skipua and 'source' in m and m['source'].startswith('UA'):
            if args.verbose:
                print("Skipping UA Content: ",m['name'])
            return
        if args.onlyofficial:
            if 'source' in m and m['source'] not in args.onlyofficial:
                if args.verbose:
                    print("Skipping unoffical content: {} from {}".format(m['name'],utils.getFriendlySource(m['source'],args)))
                return
        skip=False
        options=False
        if type(x) is str:
                subtitle=''
                if name=="name":
                    text = ET.SubElement(m, 'name')
                    #print(str(x))
                    #print(str(m))
                    text.text = utils.fixTags(x,d,args.nohtml)
                elif name=="text":
                    text = ET.SubElement(m, 'text')
                    text.text = "   " + utils.fixTags(x,d,args.nohtml)
                elif name=="nametext":
                    text = ET.SubElement(m, 'text')
                    text.text = utils.fixTags(x,d,args.nohtml)
                elif name=="list":
                    text = ET.SubElement(m, 'text')
                    text.text = "• " + utils.fixTags(x,d,args.nohtml)
                else:
                    text = ET.SubElement(m, 'text')
                    text.text = utils.fixTags(x,d,args.nohtml)
        elif type(x) is dict:
            if "type" in x:
                if x['type']=='abilityDc' or x['type']=='abilityAttackMod':
                    skip=True
            if not skip:
                if "name" in x:
                    if 'subclassTitle' in d and d['subclassTitle'] and 'optional' in attributes:
                        if subclassname:
                            SubClassFeatureName = "{}: {}".format(subclassname,x['name'])
                            flatten(SubClassFeatureName, m, args, "name")
                        else:
                            blank = ET.SubElement(m, 'text')
                            blank.text = ""
                            SubClassFeatureName = x['name']
                            flatten(SubClassFeatureName, m, args, "nametext")
                    else:
                        blank = ET.SubElement(m, 'text')
                        blank.text = ""
                        if 'type' in x and (x['type']=='entries' or x['type']=='inset'):
                            flatten(x['name'] + ":", m, args, "nametext")
                        else:
                            flatten(x['name'], m, args, "text")
                for a in x:
                    if a=="type" and x[a]=="list" and "style" in x and x["style"] == "list-hang-notitle":
                        blank = ET.SubElement(m, 'text')
                        blank.text = ""
                        for item in x["items"]:
                            if type(item) == str:
                                flatten(item, m, args, "text")
                            else:
                                flatten(item['name'], m, args, "text")
                                flatten(item['entry'], m, args, "list")
                        blank = ET.SubElement(m, 'text')
                        blank.text = ""
                    elif a=="type" and x[a]=="table" and "colLabels" in x:
                        blank = ET.SubElement(m, 'text')
                        blank.text = ""
                        if "caption" in x:
                            text = ET.SubElement(m, 'text')
                            text.text = utils.fixTags(x["caption"],d,args.nohtml)
                        text = ET.SubElement(m, 'text')
                        text.text = " | ".join([utils.remove5eShit(y)
                                                for y in x['colLabels']])
                        for row in x['rows']:
                            rowthing = []
                            for r in row:
                                if isinstance(r, dict) and 'roll' in r:
                                    rowthing.append(
                                        "{}-{}".format(
                                            r['roll']['min'],
                                            r['roll']['max']) if 'min' in r['roll'] else str(
                                            r['roll']['exact']))
                                else:
                                    rowthing.append(utils.fixTags(str(r),d,args.nohtml))
                            text = ET.SubElement(m, 'text')
                            text.text = " | ".join(rowthing)
                    elif "type" in a and x[a]=="list":
                        flatten(x['items'], m, args, "list")
                    elif a=="entries":
                        flatten(x[a], m, args, "text")
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, m, args, name)
                i += 1
    if Class.tag == 'class':
        n = ET.SubElement(Class, 'autolevel', attributes)
    else:
        n = Class
    flatten(nested_json, n, args)


def hasSubfeatureInSource(feature, args):
    for subfeature in feature['entries']:
        if type(subfeature) == dict and 'type' in subfeature and subfeature['type'] == 'options':
            for opt in subfeature['entries']:
                if opt["type"] == "refOptionalfeature":
                    optRef = opt["optionalfeature"].split('|')
                    if (len(optRef) == 1 and 'PHB' in args.onlyofficial) or \
                        (len(optRef) == 2 and optRef[1] in args.onlyofficial):
                        return True
                elif opt["type"] == "refClassFeature":
                    optRef = opt["classFeature"].split('|')
                    if (len(optRef) == 1 and 'PHB' in args.onlyofficial) or \
                        optRef[1] in args.onlyofficial:
                        return True
    return False
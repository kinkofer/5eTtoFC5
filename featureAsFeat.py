# vim: set tabstop=8 softtabstop=0 expandtab shiftwidth=4 smarttab : #
import xml.etree.cElementTree as ET
import re
import utils
import json
import os
from slugify import slugify
from shutil import copyfile

stats = {"str":"Strength","dex":"Dexterity","con":"Constitution","int":"Intelligence","wis":"Wisdom","cha":"Charisma"}

def parseInvocation(m, compendium, args):
    feat = ET.SubElement(compendium, 'feat')

    name = ET.SubElement(feat, 'name')
    name.text = "Invocation: " + m['name']

    prereqs = ET.SubElement(feat,'prerequisite')
    if 'prerequisite' in m:
        prereqs.text = getPrereqs(m)

    if 'source' in m and not args.srd:
        setSource(feat, m, args)

    bodyText = ET.SubElement(feat, 'text')
    bodyText.text = ""

    if 'entries' in m:
        bodyText.text = parseEntries(m, args)

    for match in re.finditer(r'You gain proficiency in the ([^ ]*?)( and (.*?))? skill',bodyText.text):
        bonusmod = ET.SubElement(feat, 'proficiency')
        bonusmod.text = match.group(1)
        if match.group(2) and match.group(3):
            bonusmod.text = ", " + match.group(3)


def parseInfusion(m, compendium, args):
    feat = ET.SubElement(compendium, 'feat')

    name = ET.SubElement(feat, 'name')
    name.text = "Infusion: " + m['name']

    prereqs = ET.SubElement(feat,'prerequisite')
    if 'prerequisite' in m:
        prereqs.text = getPrereqs(m)

    if 'source' in m and not args.srd:
        setSource(feat, m, args)

    bodyText = ET.SubElement(feat, 'text')
    bodyText.text = ""

    if 'entries' in m:
        bodyText.text = parseEntries(m, args)

    for match in re.finditer(r'You gain proficiency in the ([^ ]*?)( and (.*?))? skill',bodyText.text):
        bonusmod = ET.SubElement(feat, 'proficiency')
        bonusmod.text = match.group(1)
        if match.group(2) and match.group(3):
            bonusmod.text = ", " + match.group(3)


def parseManeuver(m, compendium, args):
    feat = ET.SubElement(compendium, 'feat')

    name = ET.SubElement(feat, 'name')
    name.text = "Maneuver: " + m['name']

    prereqs = ET.SubElement(feat,'prerequisite')
    if 'prerequisite' in m:
        prereqs.text = getPrereqs(m)

    if 'source' in m and not args.srd:
        setSource(feat, m, args)

    bodyText = ET.SubElement(feat, 'text')
    bodyText.text = ""

    if 'entries' in m:
        bodyText.text = parseEntries(m, args)

    for match in re.finditer(r'You gain proficiency in the ([^ ]*?)( and (.*?))? skill',bodyText.text):
        bonusmod = ET.SubElement(feat, 'proficiency')
        bonusmod.text = match.group(1)
        if match.group(2) and match.group(3):
            bonusmod.text = ", " + match.group(3)


def getPrereqs(m):
    prereq = []
    for pre in m['prerequisite']:
        if 'ability' in pre:
            if type(pre['ability']) == list:
                abilityor = []
                if all(next(iter(v.values())) == next(iter(pre['ability'][0].values())) for v in pre['ability']):
                    for v in pre['ability']:
                        for s,val in v.items():
                            abilityor.append(stats[s])
                    prereq.append("{} {} or higher".format(" or ".join(abilityor),next(iter(pre['ability'][0].values()))))
                else:
                    for v in pre['ability']:
                        for s,val in v.items():
                            abilityor.append("{} {} or higher".format(stats[k],val))
                    prereq.append(" or ".join(abilityor))
            else:
                for k,v in pre['ability'].items():
                    prereq.append("{} {} or higher".format(stats[k],v))
        if 'spellcasting' in pre and pre['spellcasting']:
            prereq.append("The ability to cast at least one spell")
        if 'proficiency' in pre:
            for prof in pre['proficiency']:
                for k,v in prof.items():
                    prereq.append("Proficiency with {} {}".format(v,k))
        if 'race' in pre:
            for r in pre['race']:
                prereq.append("{}{}".format(r['name']," ({})".format(r['subrace']) if 'subrace' in r else "").title())
        if 'spell' in pre:
            for s in pre['spell']:
                if '#c' in s:
                    prereq.append("{} cantrip".format(s.replace('#c','').title()))
                else:    
                    prereq.append("The ability to cast {}".format(s.title()))
        if 'level' in pre:
            level = pre['level']['level']
            prereq.append("{} level".format(utils.ordinal(level)))
        if 'patron' in pre:
            prereq.append("{} patron".format(pre['patron']))
        if 'pact' in pre:
            prereq.append("Pact of the {}".format(pre['pact']))
        if 'item' in pre:
            for i in pre['item']:
                prereq.append(i)
        if 'otherSummary' in pre:
            prereq.append(pre['otherSummary']['entrySummary'])
    return ", ".join(prereq)


def setSource(feat, m, args):
    sourcetext = "{} p. {}".format(
        utils.getFriendlySource(m['source'],args), m['page']) if 'page' in m and m['page'] != 0 else utils.getFriendlySource(m['source'],args)

    if 'otherSources' in m and m["otherSources"] is not None:
        for s in m["otherSources"]:
            if "source" not in s:
                continue
            sourcetext += ", "
            sourcetext += "{} p. {}".format(
                utils.getFriendlySource(s["source"],args), s["page"]) if 'page' in s and s["page"] != 0 else utils.getFriendlySource(s["source"],args)
    if 'entries' in m:
        if args.nohtml:
            m['entries'].append("Source: {}".format(sourcetext))
        else:
            m['entries'].append("<i>Source: {}</i>".format(sourcetext))
    else:
        if args.nohtml:
            m['entries'] = "Source: {}".format(sourcetext)
        else:
            m['entries'] = ["<i>Source: {}</i>".format(sourcetext)]
    if not args.nohtml:
        source = ET.SubElement(feat, 'source')
        source.text = sourcetext


def parseEntries(m, args):
    bodyText = ""

    for e in m['entries']:
        if "colLabels" in e:
            if 'caption' in e:
                bodyText += "{}\n".format(e['caption'])

            bodyText += " | ".join([utils.remove5eShit(x)
                                    for x in e['colLabels']])
            bodyText += "\n"
            for row in e['rows']:
                rowthing = []
                for r in row:
                    if isinstance(r, dict) and 'roll' in r:
                        rowthing.append(
                            "{}-{}".format(
                                r['roll']['min'],
                                r['roll']['max']) if 'min' in r['roll'] else str(
                                r['roll']['exact']))
                    else:
                        rowthing.append(utils.fixTags(str(r),m,args.nohtml))
                bodyText += " | ".join(rowthing) + "\n"
        elif "entries" in e:
            subentries = []
            if 'name' in e:
                if args.nohtml:
                    bodyText += "{}: ".format(e['name'])
                else:
                    bodyText += "<b>{}:</b> ".format(e['name'])
            for sube in e["entries"]:
                if type(sube) == str:
                    subentries.append(utils.fixTags(sube,m,args.nohtml))
                elif type(sube) == dict and "text" in sube:
                    subentries.append(utils.fixTags(sube["text"],m,args.nohtml))
                elif type(sube) == dict and sube["type"] == "list" and "style" in sube and sube["style"] == "list-hang-notitle":
                    for item in sube["items"]:
                        if type(item) == dict and 'type' in item and item['type'] == 'item':
                            if args.nohtml:
                                subentries.append("• {}: {}".format(item["name"],utils.fixTags(item["entry"],m,args.nohtml)))
                            else:
                                subentries.append("• <i>{}:</i> {}".format(item["name"],utils.fixTags(item["entry"],m,args.nohtml)))
                        else:
                            subentries.append("• {}".format(utils.fixTags(item,m,args.nohtml)))
                elif type(sube) == dict and sube["type"] == "list":
                    for item in sube["items"]:
                        if type(item) == dict and "entries" in item:
                            ssubentries = []                    
                            for sse in item["entries"]:
                                if type(sse) == str:
                                    ssubentries.append(utils.fixTags(sse,m,args.nohtml))
                                elif type(sse) == dict and "text" in sse:
                                    ssubentries.append(utils.fixTags(sse["text"],m,args.nohtml))
                                subentries.append("\n".join(ssubentries))
                        elif type(item) == dict and 'type' in item and item['type'] == 'item':
                            if args.nohtml:
                                subentries.append("• {}: {}".format(item["name"],utils.fixTags(item["entry"],m,args.nohtml)))
                            else:
                                subentries.append("• <i>{}:</i> {}".format(item["name"],utils.fixTags(item["entry"],m,args.nohtml)))
                        else:
                            subentries.append("• {}".format(utils.fixTags(item,m,args.nohtml)))
            bodyText += "\n".join(subentries) + "\n"
        else:
            if type(e) == dict and e["type"] == "list" and "style" in e and e["style"] == "list-hang-notitle":
                for item in e["items"]:
                    if args.nohtml:
                        bodyText += "• {}: {}".format(item["name"],utils.fixTags(item["entry"],m,args.nohtml)) + "\n"
                    else:
                        bodyText += "• <i>{}:</i> {}".format(item["name"],utils.fixTags(item["entry"],m,args.nohtml)) + "\n"
            elif type(e) == dict and e["type"] == "list":
                for item in e["items"]:
                    if "entries" in item:
                        subentries = []                    
                        for sube in item["entries"]:
                            if type(sube) == str:
                                subentries.append(utils.fixTags(sube,m,args.nohtml))
                            elif type(sube) == dict and "text" in sube:
                                subentries.append(utils.fixTags(sube["text"],m,args.nohtml))
                            bodyText += "\n".join(subentries) + "\n"
                    else:
                        bodyText += "• {}".format(utils.fixTags(item,m,args.nohtml)) + "\n"
            else:
                bodyText += utils.fixTags(e,m,args.nohtml) + "\n"

    bodyText = bodyText.rstrip()
    return bodyText
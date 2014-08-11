#!/usr/bin/env python
# -*- coding: utf-8
"""
@package editor
@module g.gui.metadata
@brief base editor, read/write ISO metadata, generator of widgets in editor

Classes:
 - editor::MdFileWork
 - editor::MdBox
 - editor::MdWxDuplicator
 - editor::MdItem
 - editor::MdNotebookPage
 - editor::MdMainEditor

(C) 2014 by the GRASS Development Team
This program is free software under the GNU General Public License
(>=v2). Read the file COPYING that comes with GRASS for details.

@author Matej Krejci <matejkrejci gmail.com> (GSoC 2014)
"""
import re
import os
import sys
import contextlib
from lxml import etree

import wx
from wx import ID_ANY
from wx import EVT_BUTTON
import wx.lib.scrolledpanel as scrolled

from owslib.iso import *
from jinjainfo import JinjaTemplateParser
from jinja2 import Environment, FileSystemLoader

from core.gcmd import RunCommand, GError, GMessage
from gui_core.widgets import IntegerValidator, NTCValidator, SimpleValidator,\
    TimeISOValidator, EmailValidator  # ,EmptyValidator
import mdutil

#=========================================================================
# MD filework
#=========================================================================


class MdFileWork():

    ''' initializer of metadata in OWSLib and export OWSLib object to xml by jinja templating system
    '''

    def __init__(self, pathToXml=None):
        self.path = pathToXml
        self.owslibInfo = None

    def initMD(self, path=None):
        '''
        @brief initialize metadata
        @param path: path to xml
        @return: initialized md object by input xml
        '''
        if path is None:
            self.md = MD_Metadata(md=None)
            return self.md
        else:
            io = open(path, 'r')
            str1 = ''
            for line in io.readlines():
                str1 += mdutil.removeNonAscii(line)
            io.close()
            io1 = open(path, 'w')
            io1.write(str1)
            io1.close()

            try:
                tree = etree.parse(path)
                root = tree.getroot()
                self.md = MD_Metadata(root)

                return self.md

            except Exception, e:
                GError('Error loading xml:\n' + str(e))

    def saveToXML(self, md, owsTagList, jinjaPath, outPath=None, xmlOutName=None, msg=True, rmTeplate=False):
        '''
        @note creator of xml with using OWSLib md object and jinja template
        @param md: owslib.iso.MD_Metadata
        @param owsTagList: in case if user definig template
        @param jinjaPath: path to jinja template
        @param outPath: path of exported xml
        @param xmlOutName: name of exported xml
        @param msg: gmesage info after export
        @param rmTeplate: remove template after use
        @return: initialized md object by input xml
        '''
    # if  output file name is None, use map name and add postfix
        self.dirpath = os.path.dirname(os.path.realpath(__file__))
        self.md = md
        self.owsTagList = owsTagList

        if xmlOutName is None:
            xmlOutName = 'RANDExportMD'  # TODO change to name of map
        if not xmlOutName.lower().endswith('.xml'):
            xmlOutName += '.xml'
        # if path is None, use lunch. dir
        # TODO change default folder to mapset location
        if not outPath:
            outPath = os.path.join(self.dirpath, xmlOutName)
        else:
            outPath = os.path.join(outPath, xmlOutName)
        xml = open(jinjaPath, 'r')

        str1 = ''
        for line in xml.readlines():
            line = mdutil.removeNonAscii(line)
            str1 += line
        xml.close
        io = open(jinjaPath, 'w')
        io.write(str1)
        io.close()

        # generating xml using jinja tempaltes
        head, tail = os.path.split(jinjaPath)
        env = Environment(loader=FileSystemLoader(head))
        env.globals.update(zip=zip)
        template = env.get_template(tail)
        if self.owsTagList is None:
            iso_xml = template.render(md=self.md)
        else:
            iso_xml = template.render(md=self.md, owsTagList=self.owsTagList)
        xml_file = xmlOutName

        try:
            xml_file = open(outPath, "w")
            xml_file.write(iso_xml)
            xml_file.close()

            if msg:
                GMessage('File exported to: %s' % outPath)

            if rmTeplate:
                os.remove(jinjaPath)

            return outPath

        except Exception, e:
                GError('Error writing xml:\n' + str(e))

#=========================================================================
# CREATE BOX (staticbox+button(optional)
#=========================================================================


class MdBox(wx.Panel):

    '''widget(static box) which include metadata items (MdItem)
    '''

    def __init__(self, parent, label='label'):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        self.label = label
        self.mdItems = list()
        self.stbox = wx.StaticBox(self, label=label, id=ID_ANY, style=wx.RAISED_BORDER)
        self.stbox.SetForegroundColour((0, 0, 0))
        self.stbox.SetBackgroundColour((200, 200, 200))
        self.stbox.SetFont(wx.Font(12, wx.NORMAL, wx.NORMAL, wx.NORMAL))

    def addItems(self, items, multi=True, rmMulti=False, isFirstNum=-1):
        '''
        @param items: editor::MdItems
        @param multi: true in case when box has button for duplicating box and included items
        @param rmMulti: true in case when box has button for removing box and included items
        @param isFirstNum: handling with 'add' and 'remove' button of box.
                            this param is necessary for generating editor  in editor::MdEditor.generateGUI.inBlock()
                            note: just firs generated box has 'add' buton (because is mandatory) and nex others has
                            'remove butt'
        '''
        if isFirstNum != 1:
            multi = False
            rmMulti = True

        # if not initialize in jinja template (default is true)
        if multi is None:
            multi = True

        self.panelSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.panelSizer)

        self.boxButtonSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.panelSizer.AddSpacer(10, 10, 1, wx.EXPAND)
        self.panelSizer.Add(self.boxButtonSizer, flag=wx.EXPAND, proportion=1)

        self.stBoxSizer = wx.StaticBoxSizer(self.stbox, orient=wx.VERTICAL)
        self.boxButtonSizer.Add(self.stBoxSizer, flag=wx.EXPAND, proportion=1)

        for item in items:
            self.mdItems.append(item)
            self.stBoxSizer.Add(item, flag=wx.EXPAND, proportion=1)
            self.stBoxSizer.AddSpacer(5, 5, 1, wx.EXPAND)

        if multi:
            self.addBoxButt = wx.Button(self, id=ID_ANY, size=(30, 30), label='+')
            self.boxButtonSizer.Add(self.addBoxButt, 0)
            self.addBoxButt.Bind(EVT_BUTTON, self.duplicateBox)

        if rmMulti:
            self.rmBoxButt = wx.Button(self, id=ID_ANY, size=(30, 30), label='-')
            self.boxButtonSizer.Add(self.rmBoxButt, 0)
            self.rmBoxButt.Bind(EVT_BUTTON, self.removeBox)

    def addDuplicatedItem(self, item):
        self.stBoxSizer.Add(item, flag=wx.EXPAND, proportion=1)
        self.stBoxSizer.AddSpacer(5, 5, 1, wx.EXPAND)
        self.GetParent().Layout()

    def getCtrlID(self):
        return self.GetId()

    def removeBox(self, evt):
        for item in self.mdItems:
            item.mdDescription.removeMdItem(item)
        self.GetParent().removeBox(self)

    def removeMdItem(self, mdItem, items):
        '''
        @param mdItem: object editor::MdItem
        @param items: widgets to destroy
        '''
        mdItem.mdDescription.removeMdItem(mdItem)
        for item in items:
            try:
                item.Destroy()
            except:
                pass
        self.stBoxSizer.RemovePos(-1)  # remove wxSpacer
        self.stBoxSizer.Remove(mdItem)
        self.GetParent().Layout()

    def duplicateBox(self, evt):
        duplicator = MdWxDuplicator(self.mdItems, self.GetParent(), self.label)
        clonedBox = duplicator.mdBox
        self.GetParent().addDuplicatedItem(clonedBox, self.GetId())

#===============================================================================
# DUPLICATOR OF WIDGETS-mditem
#===============================================================================


class MdWxDuplicator():

    '''duplicator of MdBox and MdItem object
    '''

    def __init__(self, mdItems, parent, boxlabel=None, mdItemOld=None, template=None):
        '''
        @param mdItems:  list of editor::MdItem
        @param parent: parent of new  duplicated box
        @param boxlabel: label of static box
        @param mdItemOld: object which will be duplicated
        @param template: in case if  'template mode' is on in editor
        '''
        # duplicate box of items
        if boxlabel:
            itemList = list()
            self.mdBox = MdBox(parent, boxlabel)
            for i in mdItems:
                try:  # check if item has multiple button
                    i.addItemButt.GetLabel()
                    multi = True
                except:
                    multi = False
                try:  # check if chckBoxEdit exists
                    i.chckBoxEdit.GetValue()
                    template = True
                except:
                    template = False

                i = i.mdDescription  # var mdDescription is  jinjainfo::MdDescription
                mdItem1 = MdItem(parent=self.mdBox,
                                 item=i,
                                 multiplicity=multi,
                                 isFirstNum=1,
                                 chckBox=template)

                itemList.append(mdItem1)

                i.addMdItem(mdItem1)  # add item with using jinjainfo::MDescription
            self.mdBox.addItems(itemList, False, True)  # fill box

        else:  # duplicate only MdItem
            self.mdItem = MdItem(parent=parent,
                                 item=mdItems,
                                 multiplicity=False,
                                 rmMulti=True,
                                 isFirstNum=-1,
                                 chckBox=template)

            try:
                if mdItems.inbox is not None:
                    mdItems.addMdItem(self.mdItem, mdItemOld)
                else:
                    mdItems.addMdItem(self.mdItem)
            except:
                mdItems.addMdItem(self.mdItem)
#=========================================================================
# METADATA ITEM (label+ctrlText+button(optional)+chckbox(template)
#=========================================================================


class MdItem(wx.BoxSizer):

    '''main building blocks of generated gui of editor
    '''

    def __init__(self, parent, item, multiplicity=None, rmMulti=False, isFirstNum=-1, chckBox=False):
        '''
        @param item: jinjainfo::MdDescription(initialized by parsing information from jinja template)
        @param multiplicity: if true- widget has button for duplicate self
        @param rmMulti: if true- widget has button for remove self
        @param isFirstNum: handling with 'add' and 'remove' button of box.
                            this param is necessary for generating editor  in editor::MdEditor.generateGUI.inBlock()
                            note: just firs generated box has 'add' buton (because is mandatory) and nex others has
                            'remove butt'
        @param chckBox: in case-True  'template editor' is on and widget has checkobox.
        '''
        wx.BoxSizer.__init__(self, wx.VERTICAL)
        self.isValid = False
        self.isChecked = False
        self.mdDescription = item
        self.chckBox = chckBox
        self.multiple = multiplicity

        if multiplicity is None:
            self.multiple = item.multiplicity

        if isFirstNum != 1:
            self.multiple = False

        if isFirstNum != 1 and item.multiplicity:
            rmMulti = True

        self.tagText = wx.StaticText(parent=parent, id=ID_ANY, label=item.name)

        if self.chckBox == False:
            if item.multiline is True:
                self.valueCtrl = wx.TextCtrl(parent, id=ID_ANY, size=(0, 70),
                                             validator=self.validators(item.type),
                                             style=wx.VSCROLL |
                                             wx.TE_MULTILINE | wx.TE_WORDWRAP |
                                             wx.TAB_TRAVERSAL | wx.RAISED_BORDER)
            else:
                self.valueCtrl = wx.TextCtrl(parent, id=wx.ID_ANY,
                                             validator=self.validators(item.type),
                                             style=wx.VSCROLL | wx.TE_DONTWRAP |
                                             wx.TAB_TRAVERSAL | wx.RAISED_BORDER | wx.HSCROLL)
        else:
            if item.multiline is True:
                self.valueCtrl = wx.TextCtrl(parent, id=ID_ANY, size=(0, 70),
                                             style=wx.VSCROLL |
                                             wx.TE_MULTILINE | wx.TE_WORDWRAP |
                                             wx.TAB_TRAVERSAL | wx.RAISED_BORDER)
            else:
                self.valueCtrl = wx.TextCtrl(parent, id=wx.ID_ANY,
                                             style=wx.VSCROLL | wx.TE_DONTWRAP |
                                             wx.TAB_TRAVERSAL | wx.RAISED_BORDER | wx.HSCROLL)

        self.valueCtrl.Bind(wx.EVT_MOTION, self.onMove)
        self.valueCtrl.SetExtraStyle(wx.WS_EX_VALIDATE_RECURSIVELY)

        if self.multiple:
            self.addItemButt = wx.Button(parent, -1, size=(30, 30), label='+')
            self.addItemButt.Bind(EVT_BUTTON, self.duplicateItem)

        if rmMulti:
            self.rmItemButt = wx.Button(parent, -1, size=(30, 30), label='-')
            self.rmItemButt.Bind(EVT_BUTTON, self.removeItem)

        if self.chckBox:
            self.chckBoxEdit = wx.CheckBox(parent, -1, size=(30, 30))
            self.chckBoxEdit.Bind(wx.EVT_CHECKBOX, self.onChangeChckBox)
            self.chckBoxEdit.SetValue(False)
            self.isChecked = False
            self.valueCtrl.Disable()

        self.createInfo()
        self.tip = wx.ToolTip(self.infoTip)

        self._addItemLay(item.multiline, rmMulti)

    def validators(self, validationStyle):

        if validationStyle == 'email':
            return EmailValidator()

        if validationStyle == 'integer':
            return NTCValidator('DIGIT_ONLY')

        if validationStyle == 'decimal':
            return NTCValidator('DIGIT_ONLY')

        if validationStyle == 'date':
            return TimeISOValidator()

        # return EmptyValidator()
        return SimpleValidator('')

    def onChangeChckBox(self, evt):
        '''current implementation of editor mode for defining templates not allowed to check
        only single items in static box. There are two cases:  all items in box are checked or not.
        '''
        if self.mdDescription.inbox:  # MdItems are in box
            try:
                items = self.valueCtrl.GetParent().mdItems
                if self.isChecked:
                        self.valueCtrl.Disable()
                        self.isChecked = False
                else:
                        self.valueCtrl.Enable()
                        self.isChecked = True

                for item in items:
                        if self.isChecked:
                            item.valueCtrl.Enable()
                            item.chckBoxEdit.SetValue(True)
                            item.isChecked = True
                        else:
                            item.valueCtrl.Disable()
                            item.chckBoxEdit.SetValue(False)
                            item.isChecked = False
            except:
                pass
        else:
            if self.isChecked:
                self.valueCtrl.Disable()
                self.isChecked = False
            else:
                self.valueCtrl.Enable()
                self.isChecked = True

    def onMove(self, evt=None):
        self.valueCtrl.SetToolTip(self.tip)

    def createInfo(self):
        """Feed for tooltip
        """
        string = ''
        if self.mdDescription.ref is not None:
            string += self.mdDescription.ref + '\n\n'
        if self.mdDescription.name is not None:
            string += 'NAME: \n' + self.mdDescription.name + '\n\n'
        if self.mdDescription.desc is not None:
            string += 'DESCRIPTION: \n' + self.mdDescription.desc + '\n\n'
        if self.mdDescription.example is not None:
            string += 'EXAMPLE: \n' + self.mdDescription.example + '\n\n'
        if self.mdDescription.type is not None:
            string += 'DATA TYPE: \n' + self.mdDescription.type + '\n\n'
        string += '*' + '\n'
        if self.mdDescription.statements is not None:
            string += 'Jinja template info: \n' + self.mdDescription.statements + '\n'

        if self.mdDescription.statements1 is not None:
            string += self.mdDescription.statements1 + '\n'
        string += 'OWSLib info:\n' + self.mdDescription.tag
        self.infoTip = string

    def removeItem(self, evt):
        """adding all items in self(mdItem) to list and call parent remover
        """
        ilist = [self.valueCtrl, self.tagText]
        try:
            ilist.append(self.rmItemButt)
        except:
            pass
        try:
            ilist.append(self.chckBoxEdit)
        except:
            pass
        self.valueCtrl.GetParent().removeMdItem(self, ilist)

    def duplicateItem(self, evt):
        '''add Md item to parent(box or notebook page)
        '''
        parent = self.valueCtrl.GetParent()
        # if parent is box
        if self.mdDescription.inbox:
            duplicator = MdWxDuplicator(mdItems=self.mdDescription,
                                        parent=parent,
                                        mdItemOld=self,
                                        template=self.chckBox)
        else:
            duplicator = MdWxDuplicator(mdItems=self.mdDescription,
                                        parent=parent,
                                        template=self.chckBox)

        clonedMdItem = duplicator.mdItem
        # call parent "add" function
        self.valueCtrl.GetParent().addDuplicatedItem(clonedMdItem, self.valueCtrl.GetId())

    def setValue(self, value):
        '''Set value & color of widgets
        in case if is template creator 'on':
            yellow: in case if value is marked by $NULL(by mdgrass::GrassMD)
            red:    if value is '' or object is not initialized. e.g. if user
                    read non fully valid INSPIRE xml with INSPIRE jinja template,
                    the gui generating mechanism will create GUI according to template
                    and all missing tags(xml)-gui(TextCtrls) will be marked by red
        '''
        if value is None or value is '':
            if self.chckBox:
                self.chckBoxEdit.SetValue(True)
                self.isChecked = True
                try:
                    self.onChangeChckBox(None)
                    self.onChangeChckBox(None)
                except:
                    pass
                self.valueCtrl.SetBackgroundColour((245, 204, 230))  # red

            self.valueCtrl.SetValue('')
            self.valueCtrl.Enable()

        elif self.chckBox and value == '$NULL':
            self.valueCtrl.SetBackgroundColour((255, 255, 82))  # yellow
            self.valueCtrl.SetValue('')

            if self.chckBox:
                self.chckBoxEdit.SetValue(True)
                self.isChecked = True
                self.valueCtrl.Enable()
                try:
                    self.onChangeChckBox(None)
                    self.onChangeChckBox(None)
                except:
                    pass

        elif value == '$NULL':
            self.valueCtrl.SetValue('')

        else:
            self.isValid = True
            self.valueCtrl.SetValue(value)

    def getValue(self):

        value = mdutil.replaceXMLReservedChar(self.valueCtrl.GetValue())
        value = value.replace('\n', '')
        value = value.replace('"', '')
        value = value.replace("'", '')
        return value

    def getCtrlID(self):
        return self.valueCtrl.GetId()

    def _addItemLay(self, multiline, rmMulti):
        self.textFieldSizer = wx.BoxSizer(wx.HORIZONTAL)
        if multiline is True:
            self.textFieldSizer.Add(self.valueCtrl, proportion=1, flag=wx.EXPAND)
        else:
            self.textFieldSizer.Add(self.valueCtrl, proportion=1)

        if self.multiple:
            self.textFieldSizer.Add(self.addItemButt, 0)

        if rmMulti:
            self.textFieldSizer.Add(self.rmItemButt, 0)

        if self.chckBox:
            self.textFieldSizer.Add(self.chckBoxEdit, 0)

        self.Add(item=self.tagText, proportion=0)
        self.Add(item=self.textFieldSizer, proportion=0, flag=wx.EXPAND)

#=========================================================================
# ADD NOTEBOOK PAGE
#=========================================================================


class MdNotebookPage(scrolled.ScrolledPanel):

    """
    every notebook page is initialized by jinjainfo::MdDescription.group (label)
    """

    def __init__(self, parent):
        scrolled.ScrolledPanel.__init__(self, parent=parent, id=wx.ID_ANY)
        self.items = []
        self.SetupScrolling()
        self._addNotebookPageLay()
        self.sizerIndexDict = {}
        self.sizerIndex = 0

    def _addNotebookPageLay(self):
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.mainSizer)

    def _getIndex(self):
        '''
        index for handling position of editor::MdBox,MdItem in editor::MdNotebookPage(self).
        Primary for correct duplicating Boxes or items on notebook page
        '''
        self.sizerIndex += 1
        return self.sizerIndex

    def addItem(self, item):
        '''
        @param item: can be editor::MdBox or editor::MDItem
        '''
        if isinstance(item, list):
            for i in item:
                if isinstance(i, list):
                    for ii in i:
                        self.sizerIndexDict[ii.getCtrlID()] = self._getIndex()
                        self.mainSizer.Add(ii, proportion=0, flag=wx.EXPAND)
                else:
                    self.sizerIndexDict[i.getCtrlID()] = self._getIndex()
                    self.mainSizer.Add(i, proportion=0, flag=wx.EXPAND)
        else:
            self.sizerIndexDict[item.getCtrlID()] = self._getIndex()
            self.mainSizer.Add(item, proportion=0, flag=wx.EXPAND)

    def addDuplicatedItem(self, item, mId):
        '''adding duplicated object to sizer to  position after parent
        '''
        self.items.append(item)
        posIndex = self.sizerIndexDict[mId]
        self.mainSizer.Insert(posIndex, item, proportion=0, flag=wx.EXPAND)
        self.SetSizerAndFit(self.mainSizer)
        self.GetParent().Refresh()

    def removeBox(self, box):
        box.Destroy()
        self.SetSizerAndFit(self.mainSizer)

    def removeMdItem(self, mdDes, items):
        '''Remove children
        @param mdDes: editor::MdItem.mdDescription
        @param items: all widgets to remove of MdItem
        '''
        mdDes.mdDescription.removeMdItem(mdDes)  # remove from jinjainfi:MdDEscription object
        for item in items:
            item.Destroy()
        self.SetSizerAndFit(self.mainSizer)

#=========================================================================
# MAIN FRAME
#=========================================================================


class MdMainEditor(wx.Panel):

    '''
    main functions : self.generateGUI(): generating GUI from: editor:MdItem,MdBox,MdNotebookPage
                     self.createNewMD(): filling OWSLib.iso.MD_Metadata by values from generated gui
                     self.defineTemplate(): creator of predefined templates in template editor mode
    '''

    def __init__(self, parent, templatePath, xmlMdPath, templateEditor=False):
        '''
        @param templatePath: path to jinja template for generating gui of editor
        @param xmlMdPath: path of xml for init Editor
        @param templateEditor: mode-creator of template
        '''
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        self.mdo = MdFileWork()
        self.md = self.mdo.initMD(xmlMdPath)
        self.templateEditor = templateEditor
        self.templatePath = templatePath

        self.jinj = JinjaTemplateParser(self.templatePath)
        # list of object MdDescription
        self.mdDescription = self.jinj.mdDescription
        # string of tags from jinja template (loops and OWSLib objects)
        self.mdOWSTagStr = self.jinj.mdOWSTagStr
        self.mdOWSTagStrList = self.jinj.mdOWSTagStrList  #

        self.generateGUI()
        self._layout()

#----------------------------------------------------------- GUI GENERATOR START
    def executeStr(self, stri, mdDescrObj):
        '''note- exec cannot be in sub function
        for easy understanding to product of self.generateGUI()- print stri
        '''
        # print stri
        exec stri

    def plusC(self, num=None):
        '''iterator for handling jinja teplate items in self.generateGUI and self.createNewMD

        '''
        if num is None:
            num = 1
        self.c += num
        if self.c >= self.max:
                self.c -= 1  # ensure to'list out of bounds'
                self.stop = True

    def minusC(self, num=None):
        '''iterator for handling jinja teplate items in  self.generateGUI and self.createNewMD
        '''
        if num is None:
            num = 1
        self.c -= num
        if self.c <= self.max:
            self.stop = False

    def generateGUI(self):
        '''
        @var tagStringLst:  tagStringLst is self.mdOWSTagStr in list.
                            Item=line from jinja template(only lines with owslib objects and loops)
        @var mdDescrObj:    list of MdDescription() objects inicialized\
                            by information from jinja t.
        @var self.c:        index of var: tagStringLst and var: self.mdDescription
        @var markgroup:     markers of created list in GUI notebook
        @var self.max:      length of tagStringLst and mdDescrObj
        @var self.stop:     index self.c is increasing  by function plusC(),\
                            that care about not exceeding the index
        HINT: print param stri in self.executeStr()
        '''
        def prepareStatements():
            '''in jinja template are difining some py-function specificaly:
            e.g. |length=len
            also statements with pythonic 'zip' must be prepare specifically for generator of GUI
            '''
            for c in range(self.max):
                if '|length' in str(tagStringLst[c]):
                    a = tagStringLst[c]
                    a = a.replace('|length', ')').replace('if ', 'if len(self.')
                    tagStringLst[c] = a
                if 'zip(' in tagStringLst[c]:
                    sta = tagStringLst[c]
                    tagStringLst[c] = sta.replace('md.', 'self.md.')

        def chckIfJumpToLoop(sta):
            '''if loaded xml not include tags(OWSLib object) from jinja template, this function will
                    generate sample of item(marked by red in GUI-template mode).
            @note: in case of sub statements e.g. metadata-keywords is need to check booth statements
            @param sta: statements of the loop
            for understanding print param for self.executeStr()
            '''
            self.isValidS = False
            staTMP = sta
            if not '\t'in staTMP:
                tab = '\t'
                tab1 = ''
                staTMP = staTMP + ":\n" + tab + 'self.isValidS=True'
            else:
                tab = '\t'
                tab1 = '\t'
                staTMP = staTMP.replace('\t', '') + ":\n" + tab + 'self.isValidS=True'

            try:  # if loop for in for
                self.executeStr(staTMP, False)
            except:
                staTMP = self.staTMP.replace('self.isValidS=True', '') + '\n\t' + staTMP.replace('\t', '\t\t')
                self.executeStr(staTMP, False)

            self.staTMP = staTMP
            if self.isValidS:
                return sta
            else:
                return tab1 + 'for n in range(1)'

        def inBlock():
            '''This part of code build string-code for executing. This can happend if is necassary to use statements
                to generate gui(OWSLib objects in list). The block of code is building from "statement" which is represended by OWSLib object.
                In case if OWSLib object is non initialized(metadata missing), function chckIfJumpToLoop() replace statements by "for n in range(1)".
            @var IFStatements: True= string is IF statements
            @var loop: current statements, mostly loop FOR
            @var str1: final string for execute
            @var box:  True if editor::MdItems is in editor::MdBox
            @var isValid: True in case if OWSLib object in statement is initialized. False= statements is 'for n in range(1)'
            '''
            IFStatements = False
            statements = tagStringLst[self.c - 1]
            if 'if' in statements.split():
                IFStatements = True
            loop = statements.replace(' md.', ' self.md.')
            looptmp = chckIfJumpToLoop(loop)
            str2 = 'numOfSameBox=0\n'
            str2 += looptmp

            str2 += ':\n'
            str2 += '\t' + 'self.ItemList=list()\n'  # initialize list
            str2 += '\t' + 'numOfSameBox+=1\n'

            box = False
            if self.mdDescription[self.c].inbox:
                box = True
                str2 += '\t' + 'box=MdBox(self.nbPage,mdDescrObj[' + str(self.c) + '].inbox)\n'  # add box

            str1 = str2
            while '\t' in tagStringLst[self.c] and self.stop is False:
                if  'for' not in str(tagStringLst[self.c]).split()\
                        and 'if' not in str(tagStringLst[self.c]).split():

                    value = str(self.mdOWSTagStrList[self.c])
                    str1 += '\t' + 'self.mdDescription[' + str(self.c) + "].addStatements('" + loop + "')\n"

                    if box:
                        str1 +=     '\t' + \
                            'it=MdItem(parent=box,item=mdDescrObj[' + str(self.c) + '],isFirstNum=numOfSameBox,chckBox=self.templateEditor)\n'
                    else:
                        str1 +=     '\t' + \
                            'it=MdItem(parent=self.nbPage,item=mdDescrObj[' + str(self.c) + '],isFirstNum=numOfSameBox,chckBox=self.templateEditor)\n'

                    if self.isValidS:  # if metatdata are loaded to owslib
                        if IFStatements:
                            str1 += '\t' + 'it.setValue(self.' + str(value) + ')\n'
                        else:
                            str1 += '\t' + 'it.setValue(' + str(value) + ')\n'
                    else:
                        if IFStatements:
                            str1 += '\t' + 'it.setValue("")\n'
                        else:
                            str1 += '\t' + 'it.setValue("")\n'

                    str1 += '\t' + 'self.mdDescription[' + str(self.c) + '].addMdItem(it)\n'
                    str1 += '\t' + 'self.ItemList.append(it)\n'
                    tab = '\t'
                    self.plusC()

                else:  # if statements in statements
                    statements = tagStringLst[self.c]
                    str2 = ''
                    keyword = False

                    if '["keywords"]' in statements:
                        keyword = True
                        str2 += '\t' + 'self.keywordsList=[]\n'

                    str2 += '\t' + 'numOfSameItem=0\n'
                    loop2 = statements.replace(' md.', ' self.md.')
                    looptmp1 = chckIfJumpToLoop(loop2)
                    str2 += looptmp1 + ':\n'
                    self.plusC()
                    str1 += str2
                    while '\t\t' in tagStringLst[self.c] and self.stop is False:
                        value = str(self.mdOWSTagStrList[self.c])
                        # save information about loops
                        str1 += '\t\t' + 'numOfSameItem+=1\n'
                        str1 += '\t\t' + 'self.mdDescription[' + str(self.c) + "].addStatements('" + loop + "')\n"
                        str1 += '\t\t' + 'self.mdDescription[' + str(self.c) + "].addStatements1('" + loop2 + "')\n"

                        if box:
                            str1 += '\t\t' + \
                                'it=MdItem(parent=box,item=mdDescrObj[' + str(self.c) + '],isFirstNum=numOfSameItem,chckBox=self.templateEditor)\n'
                        else:
                            str1 += '\t\t' + \
                                'it=MdItem(self.nbPage,mdDescrObj[' + str(self.c) + '],isFirstNum=numOfSameItem,chckBox=self.templateEditor)\n'

                        if self.isValidS:
                            str1 += '\t\t' + 'it.setValue(' + str(value) + ')\n'
                        else:
                            str1 += '\t\t' + 'it.setValue("")\n'

                        str1 += '\t\t' + 'self.ItemList.append(it)\n'
                        if keyword:
                            str1 += '\t\t' + 'self.keywordsList.append(it)\n'
                            str1 += '\t' + 'self.mdDescription[' + str(self.c) + '].addMdItem(self.keywordsList)\n'
                        else:
                            str1 += '\t\t' + 'self.mdDescription[' + str(self.c) + '].addMdItem(it)\n'

                        tab = '\t\t'
                        self.plusC()
            if box:
                str1 += tab +\
                    'box.addItems(items=self.ItemList,multi=mdDescrObj[self.c].inboxmulti,isFirstNum=numOfSameBox)\n'
                str1 += tab + 'self.nbPage.addItem(box)\n'
            else:
                str1 += tab + 'self.nbPage.addItem(self.ItemList)\n'

            self.executeStr(str1, mdDescrObj)

#--------------------------------------------------------------------- INIT VARS
        self.notebook = wx.Notebook(self)
        markgroup = []  # notebok panel marker
        tagStringLst = self.mdOWSTagStrList
        mdDescrObj = self.mdDescription  # from jinja
        self.c = 0
        self.stop = False
        self.max = len(mdDescrObj)
        prepareStatements()
        self.notebokDict = {}
# --------------------------------------------- #START of the loop of genereator
        while self.stop is False:  # self.stop is managed by   def plusC(self):
            group = mdDescrObj[self.c].group

            if group not in markgroup:  # if group is not created
                markgroup.append(group)  # mark group
                self.nbPage = MdNotebookPage(self.notebook)
                self.notebook.AddPage(self.nbPage, mdDescrObj[self.c].group)
                self.notebokDict[mdDescrObj[self.c].group] = self.nbPage
            else:
                self.nbPage = self.notebokDict[mdDescrObj[self.c].group]

            # if  statements started
            if '\t' in tagStringLst[self.c] and self.stop is False:
                inBlock()
            # if is just singe item without statements
            elif 'for' not in str(tagStringLst[self.c]).split() and 'if' not in str(tagStringLst[self.c]).split():
                it = MdItem(parent=self.nbPage, item=mdDescrObj[self.c], chckBox=self.templateEditor)
                value = 'self.' + str(self.mdOWSTagStrList[self.c]).replace('\n', '')
                value = eval(value)
                if value is None:
                    value = ''

                it.setValue(value)
                self.mdDescription[self.c].addMdItem(it)
                self.nbPage.addItem(it)
                self.plusC()
            else:
                self.plusC()
        if self.templateEditor:
            self.refreshChkboxes()

    def refreshChkboxes(self):
        '''In case if template editor is on, after generateing gui si
         obligatory to refresh checkboxes
        '''
        for item in self.mdDescription:
            for i in item.mdItem:
                try:
                    i.onChangeChckBox(None)
                    i.onChangeChckBox(None)
                except:
                    pass
#----------------------------------------------------------- GUI GENERATOR END

    def defineTemplate(self):
        '''Main function for generating jinja template in mode "template editor"
        Every widget MdItem  are represented by 'jinja tag'. Not checked widget= tag in jinja template will be replaced by
        listo of string with string of replaced tag. In rendering template this produce  holding(non removing) jinja-tag from template.
        In case if widget is checked= rendering will replace OWSLib obect by filled values( like in normal editing mode)
        @var finalTemplate:    string included final jinja template
        '''
        try:
            template = open(self.templatePath, 'r')
        except Exception, e:
            GError('Error loading template:\n' + str(e))

        owsTagList = list()
        indexowsTagList = 0
        finalTemplate = ''
        chcked = False
        forST = 0
        ifST = 0
        forSTS = False
        ifSTS = False

        for line in template.readlines():
            if '{% for' in line:
                forSTS = True  # handler for correct end statements in jinja template
                forST += 1

            if '{% if' in line:
                ifSTS = True  # handler for correct end statements in jinja template
                ifST += 1
            # iterate over all jinjainfo::MdDescription.selfInfoString and finding match with string in xml file(line)
            for r, item in enumerate(self.mdDescription):
                str1 = item.selfInfoString
                if str1 in line:            #
                    try:
                        if item.mdItem[0].isChecked == False:
                            chcked = True
                    except:
                        try:
                            if self.mdDescription[r + 1].mdItem[0].isChecked == False:
                                chcked = True
                        except:
                            try:
                                if self.mdDescription[r + 2].mdItem[0].isChecked == False:
                                    chcked = True
                            except:
                                try:
                                    if self.mdDescription[r + 3].mdItem[0].isChecked == False:
                                        chcked = True
                                except:
                                    pass
                    if chcked:  # chckbox in gui
                        if forSTS:
                            forSTS = False
                            forST -= 1

                        if ifSTS:
                            ifSTS = False
                            ifST -= 1

                        owsTagList.append(str1)
                        templateStr = '{{ owsTagList[' + str(indexowsTagList) + '] }}'
                        indexowsTagList += 1

                        line = line.replace(str1, templateStr)
                        tag = '{{ ' + item.tag + ' }}'
                        line = line.replace(tag, templateStr)
                        finalTemplate += line
                        continue

            if chcked == False:
                    if '{% endfor -%}' in line and forST == 0:
                        str1 = '{% endfor -%}'
                        owsTagList.append(str1)
                        templateStr = '{{ owsTagList[' + str(indexowsTagList) + '] }}'
                        indexowsTagList += 1

                        line = line.replace(str1, templateStr)
                        tag = '{{' + item.tag + '}}'
                        line = line.replace(tag, templateStr)
                        finalTemplate += line

                    elif '{% endif -%}' in line and ifSTS == 0:
                        str1 = '{% endif -%}'
                        owsTagList.append(str1)
                        templateStr = '{{ owsTagList[' + str(indexowsTagList) + '] }}'
                        indexowsTagList += 1

                        line = line.replace(str1, templateStr)
                        tag = '{{' + item.tag + '}}'
                        line = line.replace(tag, templateStr)
                        finalTemplate += line

                    else:
                        finalTemplate += line
            chcked = False
        head, tail = os.path.split(self.templatePath)
        tail = 'EXPT' + tail
        self.templatePath = os.path.join(head, tail)
        templateOut = open(self.templatePath, 'w')
        templateOut.write(finalTemplate)
        templateOut.close()

        return owsTagList
#----------------------------------------- FILL OWSLib BY EDITED METADATA IN GUI

    def executeStr1(self, stri, item):
        '''note- exec cannot be in sub function
        for easy understanding to product of self.createNewMD()- print stri
        '''
        # print stri
        exec stri

    def createNewMD(self, evt=None):
        '''Main function for exporting metadata from filled widgets .
           Initializing owslib object by metadata from gui(export of metadata)
        '''
        def prepareStatements():
            '''replacing some specific declaration of python function in jinja template
            '''
            for c in range(self.max):
                if '|length' in str(mdDes[c].tag):
                    a = mdDes[c].tag
                    a = a.replace('|length', ')').replace('if ', 'if len(self.')
                    mdDes[c].tag = a
                if '|length' in str(mdDes[c].statements):
                    a = mdDes[c].statements
                    a = a.replace('|length', ')').replace('if ', 'if len(self.')
                    mdDes[c].statements = a
                if '|length' in str(mdDes[c].statements1):
                    a = mdDes[c].statements1
                    a = a.replace('|length', ')').replace('if ', 'if len(self.')
                    mdDes[c].statements1 = a

        def chckIf1Statements():
            '''Return true if next item in jinjainfo::MdDescription is statement
            '''
            try:
                if mdDes[self.c + 1].statement:
                    return True
                else:
                    return False
            except:
                return False

        def chckIf2xStatements():
            '''Return true if next two items in jinjainfo::MdDescription are reprsenting statements
            '''
            if 'if'in mdDes[self.c].tag.split() or 'for' in mdDes[self.c].tag.split():
                try:
                    if 'if'in mdDes[self.c + 1].tag.split() or 'for'in mdDes[self.c + 1].tag.split():
                        return True
                    else:
                        return False
                except:
                    return False

        def noneStatements():
            '''Without condition or loop
            '''
            str1 = ''
            for wxCtrl in mdDes[self.c].mdItem:
                if wxCtrl.getValue() is not None:
                    str1 += 'self.' + mdDes[self.c].tag + '="' + str(wxCtrl.getValue()) + '"\n'
                    self.executeStr1(str1, mdDes[self.c])
                    str1 = ''
            self.plusC()

        def inStatements():
            '''possible combinations of statements
            (1)    IF
                        item
                ----------------------------------------------------
            (2)    for
            (2.1)          item (with init OWSLib object)
                       "or"
            (2.2)          item (without init)
                           item with ZIP
            '''
            cTmp = self.c
            tag = str(mdDes[cTmp].tag).split()

            tag1 = 'self.' + str(tag[-1])
            tag = 'self.' + str(tag[-1]) + '.append(self.val)\n'

            self.plusC()
            # statements of current item
            stat = mdDes[self.c].statements
            str1 = ''
            leng = len(mdDes[self.c].mdItem)

            # (2.1) IF NECESSARY TO INITIALIZE OWSLIB OBJECT
            if mdDes[cTmp].object and 'if' not in mdDes[cTmp].tag.split():
                objStr = 'self.val=' + mdDes[cTmp].object + '\n'

                for n in range(leng):
                    numOfItems = 0
                    str1 += objStr
                    while mdDes[self.c].statements == stat and self.stop is False:
                        metadata = re.split(r'[.]', mdDes[self.c].tag)
                        metadata[0] = 'self.val.'
                        str1 += ''.join(metadata) + "='"\
                            + str(mdDes[self.c].mdItem[n].getValue()) + "'\n"
                        self.plusC()
                        numOfItems += 1

                    str1 += tag
                    self.executeStr1(str1, False)
                    str1 = ''
                    self.minusC(numOfItems)

                self.plusC(numOfItems)
            # (2.2)no init and py ZIP'
            elif 'for' in mdDes[cTmp].tag.split() and mdDes[cTmp].object is None and ' zip(' in mdDes[cTmp].tag:
                leng = len(mdDes[self.c].mdItem)
                tag1 = mdutil.findBetween(mdDes[cTmp].tag, 'zip(', ')').split(',')

                for n in range(leng):
                    numOfItems = 0
                    while mdDes[self.c].statements == stat and self.stop is False:
                        str1 += 'self.' + tag1[numOfItems] + ".append('" + mdDes[self.c].mdItem[n].getValue() + "')\n"
                        self.plusC()
                        numOfItems += 1

                    self.executeStr1(str1, False)
                    str1 = ''
                    self.minusC(numOfItems)

                self.plusC(numOfItems)
            # 'no init FOR'
            elif 'for' in mdDes[cTmp].tag.split() and mdDes[cTmp].object is None:
                leng = len(mdDes[self.c].mdItem)
                numOfItems = 0
                for n in range(leng):
                    numOfItems = 0
                    while mdDes[self.c].statements == stat and self.stop is False:
                        str1 += tag1 + ".append('" + mdDes[self.c].mdItem[n].getValue() + "')\n"
                        self.plusC()
                        numOfItems += 1

                    self.executeStr1(str1, False)
                    str1 = ''
                    self.minusC(numOfItems)

                self.plusC(numOfItems)
            # (1)'no init IF'
            elif 'if' in mdDes[cTmp].tag.split():

                objStr = mdDes[cTmp].tag.replace(' md.', ' self.md.') + ':\n'

                for n in range(leng):
                    numOfItems = 0
                    while mdDes[self.c].statements == stat and self.stop is False:
                        metadata = 'self.' + mdDes[self.c].tag
                        str1 += ''.join(metadata) + "='"\
                            + str(mdDes[self.c].mdItem[n].getValue()) + "'\n"
                        self.plusC()
                        numOfItems += 1

                    self.minusC(numOfItems)
                    self.executeStr1(str1, False)
                    str1 = ''
                self.plusC(numOfItems)

        def in2Statements():
            '''possible combinations of statements
            (1)    IF:
                       FOR:
            (1.1)           item (with init OWSLib object)
                            "or"
            (1.2)           item (without init)
                ----------------------------------------------------
            (2)     FOR:
                        FOR:(implemented fixedly just for MD-keywords)
            (2.1)            item (with init OWSLib object)
                             "or"
            (2.2)            item (without init)
            '''
            prepareStatements()
            cTmp = self.c
            cTmp1 = self.c + 1
            tag = str(mdDes[cTmp].tag).split()
            tag1 = str(mdDes[cTmp1].tag).split()
            stat = mdDes[self.c + 2].statements

            append = 'self.' + str(tag1[-1]) + '.append(self.val)\n'
            appendNoInit = 'self.' + str(tag1[-1])
            # (1)
            # if statements-if in jinja template=skip and do single loop
            if 'if' in tag and 'for' in tag1:
                leng = len(mdDes[self.c + 2].mdItem)
                # (1.1)
                if mdDes[cTmp1].object:
                    condition = mdDes[cTmp].tag.replace(' md.', ' self.md.') + ':\n'
                    objectOWSLib = '\t' + 'self.val=' + mdDes[cTmp1].object + '\n'
                    condition2 = '\t' + mdDes[cTmp1].tag.replace(' md.', ' self.md.') + ':\n'
                    self.plusC()
                    self.plusC()

                    for n in range(leng):
                        numOfItems = 0
                        str1 = condition + '\n'
                        str1 += condition2 + '\n'
                        str1 += '\t' + objectOWSLib + '\n'

                        while mdDes[self.c].statements == stat and self.stop is False:
                            metadata = re.split(r'[.]', mdDes[self.c].tag)
                            metadata[0] = '\t\tself.val'
                            str1 += ''.join(metadata) + "='" + str(mdDes[self.c].mdItem[n].getValue()) + "'\n"
                            self.plusC()
                            numOfItems += 1

                        str1 += '\t\t' + append
                        self.executeStr1(str1, False)
                        str1 = ''
                        self.minusC(numOfItems)
                    self.plusC(numOfItems)
                # (1.2)"if and for "
                else:
                    self.plusC()
                    self.plusC()
                    numOfItems = 0
                    size = len(mdDes[self.c].mdItem)
                    for n in range(size):
                        numOfItems = 0
                        str1 = ''

                        while mdDes[self.c].statements == stat and self.stop is False:
                            str1 += appendNoInit + '.append("' + mdDes[self.c].mdItem[n].getValue() + '")\n'
                            self.plusC()
                            numOfItems += 1

                        self.executeStr1(str1, False)
                        self.minusC(numOfItems)
                    self.plusC(numOfItems)
            # (2) only keywords  (dict)
            elif 'for' in tag and 'for' in tag1:  #
                self.plusC()  # skip staementes 2x
                self.plusC()
                numOfkwGroup = len(mdDes[self.c + 1].mdItem)
                for n in range(numOfkwGroup):
                    kw = {}
                    kw['keywords'] = []
                    try:
                        keyWordLen = len(mdDes[self.c].mdItem[n])
                        for k in range(keyWordLen):
                                kw['keywords'].append(mdDes[self.c].mdItem[n][k].getValue())
                    except:
                        kw['keywords'].append(mdDes[self.c].mdItem[n].getValue())

                    kw['type'] = None
                    kw['thesaurus'] = {}
                    kw['thesaurus']['title'] = mdDes[self.c + 1].mdItem[n].getValue()
                    kw['thesaurus']['date'] = mdDes[self.c + 2].mdItem[n].getValue()
                    kw['thesaurus']['datetype'] = mdDes[self.c + 3].mdItem[n].getValue()
                    self.md.identification.keywords.append(kw)

                self.plusC()
                self.plusC()
                self.plusC()
                self.plusC()
#------------------------------------------------------------------------------ next function
        self.mdo = MdFileWork()
        self.md = self.mdo.initMD()
        # most of object from OWSLib is initialized in configure file
        dirpath = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(dirpath, 'config', 'init_md')
        mdInitData = open(path, 'r')
        mdExec = mdInitData.read()
        self.executeStr1(mdExec, None)

        self.c = 0
        self.stop = False
        self.max = len(self.mdDescription)
        mdDes = self.mdDescription

        while self.stop is False:
            # if no statements
            if mdDes[self.c].statements is None\
                    and 'if' not in mdDes[self.c].tag.split()\
                    and 'for' not in mdDes[self.c].tag.split():
                noneStatements()

            # if 2x statements
            elif chckIf2xStatements():
                in2Statements()

            # if 1x statements
            elif chckIf1Statements:
                inStatements()

        return self.md
#------------------------------------ END- FILL OWSLib BY EDITED METADATA IN GUI

    def exportToXml(self, jinjaPath, outPath, xmlOutName, msg):
        self.createNewMD()
        self.mdo.saveToXML(self.md, None, jinjaPath, outPath, xmlOutName, msg)

    def exportTemplate(self, jinjaPath, outPath, xmlOutName):
        self.templatePath = jinjaPath
        owsTagList = self.defineTemplate()
        self.createNewMD()
        self.mdo.saveToXML(self.md, owsTagList,
                           self.templatePath,
                           outPath,
                           xmlOutName,
                           msg=True,
                           rmTeplate=True)
#------------------------------------------------------------------------ LAYOUT

    def _layout(self):
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.mainSizer)
        noteSizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook.SetSizer(noteSizer)
        self.mainSizer.Add(self.notebook, proportion=1, flag=wx.EXPAND)
        self.Show()
#----------------------------------------------------------------------
if __name__ == "__main__":
    app = wx.App(False)
    frame = MdMainEditor()
    app.MainLoop()
import mimetypes
import os
import zipfile
from io import BytesIO
from zope.lifecycleevent import modified

import plone.api
from Products.CMFPlone import utils
from plone.app.textfield import RichText
from plone.app.textfield.value import RichTextValue
from plone.autoform.form import AutoExtensibleForm
from plone.i18n.normalizer.interfaces import IFileNameNormalizer
from plone.rfc822.interfaces import IPrimaryFieldInfo
from z3c.form import button, form
from zope.component import getUtility
from zope.container.interfaces import INameChooser

from .. import _
from ..interfaces import IUnzipForm

import html
#from bs4 import BeautifulStoneSoup
import cgi

import lxml.html.clean

class Unzipper(AutoExtensibleForm, form.Form):
    ignoreContext = True

    schema = IUnzipForm

    @button.buttonAndHandler(_('Unzip'))
    def unzipper(self, action):
        """ unzip contents """
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        zipf = data['file']
        force_files = data['force_files']
        self.unzip(zipf, force_files=force_files)

        plone.api.portal.show_message(_("Your content has been imported."), self.request, type="info")
        return self.request.response.redirect(self.context.absolute_url())

    def updateActions(self):
        super().updateActions()
        list(self.actions.values())[0].addClass("context")

    def unzip(self, zipf, force_files=False):
        zipper = zipfile.ZipFile(BytesIO(zipf.data), 'r')

        for name in zipper.namelist():
            path, file_name = os.path.split(name)
            if file_name:
                stream = zipper.read(name)
                curr = self.context
                for folder in [f for f in path.split('/') if f]:
                    folder = folder.replace('%20', '-')
                    try:
                        curr = curr[folder]
                    except KeyError:
                        curr = plone.api.content.create(type='Folder', container=curr, id=folder, title=folder)

                content_type = mimetypes.guess_type(file_name)[0] or ""
                self.factory(file_name, content_type, stream, curr, force_files)

                plone.api.portal.show_message(_('Zip file imported'), self.request, type="info")
        self.request.response.redirect(self.context.absolute_url())

    def factory(self, name, content_type, data, container, force_files):
        ctr = plone.api.portal.get_tool('content_type_registry')
        portal_type = ctr.findTypeName(name.lower(), content_type, '')
        if force_files and portal_type not in ('File', 'Image'):
            portal_type = 'File'
        elif not portal_type:
            portal_type = 'File'

        normalizer = getUtility(IFileNameNormalizer)
        chooser = INameChooser(self.context)
        newid = chooser.chooseName(normalizer.normalize(name), self.context.aq_parent)

        newid = newid.lower()
        newid = newid.replace('%20', '-')
        newid = newid.replace('.html', '')
        newid = newid.replace('.htm', '')
        name = name.replace('.html', '')
        name = name.replace('.htm', '')
        name = name.replace('.jpeg', '')
        name = name.replace('.jpg', '')


        #obj = plone.api.content.create(container=container, type=portal_type, id=newid, title=name)

        try:
            obj = container[newid]
        except KeyError:
            obj = plone.api.content.create(container=container, type=portal_type, id=newid, title=name)

        primary_field = IPrimaryFieldInfo(obj)
        if isinstance(primary_field.field, RichText):
            #setattr(obj, primary_field.fieldname, RichTextValue(data))

            newvalue = data.decode('Windows-1252')
            #newvalue = newvalue.replace('\t\n', '<')
            nvalue = lxml.html.clean.clean_html(newvalue)
            obj.text = RichTextValue(nvalue)

        else:
            setattr(obj, primary_field.fieldname, primary_field.field._type(data, filename=utils.safe_unicode(name)))
        modified(obj)

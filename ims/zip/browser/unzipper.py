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
#from bs4 import BeautifulSoup

from .. import _
from ..interfaces import IUnzipForm


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
                    try:
                        curr = curr[folder]
                    except KeyError:
                        curr = plone.api.content.create(type='Folder', container=curr, id=folder.lower(), title=folder)

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
        newid = chooser.chooseName(normalizer.normalize(name), self.context.aq_parent).lower()

        obj = plone.api.content.create(container=container, type=portal_type, id=newid, title=name)
        primary_field = IPrimaryFieldInfo(obj)


        if isinstance(primary_field.field, RichText):
            setattr(obj, primary_field.fieldname, RichTextValue(data))
            html_text = RichTextValue(data).output

            #search html for title tag (used for index.html files)
            #put a check for obj.title == 'index.html'
            #soup = BeautifulSoup(html_text, 'html.parser')
            #"hack", just try instead of 'check for title tag present'
            # if obj.title == 'index.html':
            #    try:
            #        title_text = soup.find("title").text or None
            #        if title_text:
            #            obj.title = title_text
            #except:
            #    #probably just keep the title as it is (?)
            #    #To do: 'Beautify' file name ?
            #        newtitle = ''

        else:
            setattr(obj, primary_field.fieldname, primary_field.field._type(data, filename=utils.safe_unicode(name)))
        modified(obj)

        #import pdb; pdb.set_trace()
        #For images, python 3.9 (?)
        #url.removesuffix('.jpg')
        new_title = obj.title.strip('.htm').strip('.jpg').strip('.png')
        obj.title = new_title

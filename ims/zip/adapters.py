from zope import interface, component
from Products.CMFCore.interfaces import ISiteRoot
from plone.app.blob.interfaces import IATBlob, IATBlobImage
from plone.rfc822.interfaces import IPrimaryFieldInfo
from Products.ATContentTypes.interfaces.file import IATFile
from ims.zip.interfaces import IZippable

class AdapterBase(object):
    """ provide __init__ """
    def __init__(self, context):
        self.context = context
    def extension(self):
      return ''
    def zippable(self):
      return ''

class FileZip(AdapterBase):
    """ for File type """
    def zippable(self):
      primary_field = IPrimaryFieldInfo(self.context)
      return primary_field.value.data
    def extension(self):
      id = self.context.getId()
      primary_field = IPrimaryFieldInfo(self.context)
      fn = primary_field.value.filename or id
      return id.split('.')[-1] != fn.split('.')[-1] and '.'+fn.split('.')[-1] or ''

class ImageZip(FileZip):
    """ for Image type """

class DocumentZip(AdapterBase):
    """ for Document type"""
    def zippable(self):
      template = '<html><body>%(header)s%(description)s%(text)s</body></html>'

      header = self.context.title and '<h1>%s</h1>' % self.context.title or ''
      description = self.context.description and '<p class="description">%s</p>' % self.context.description or ''
      text = self.context.text.raw

      html = template % {'header':header,'description':description,'text':text}
      return html
    def extension(self):
      return '.html'
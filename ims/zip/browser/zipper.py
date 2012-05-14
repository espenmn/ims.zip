import zipfile, os
from zope import interface, component
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from ims.zip.interfaces import IZippable

class ZipPrompt(BrowserView):
  """ confirm zip """
  def __init__(self,context,request):
    self.context=context
    self.request=request

class Zipper(BrowserView):
  """ Zips content to a temp file """
  def __init__(self,context,request):
    self.context=context
    self.request=request

  def __call__(self):
    self.request.RESPONSE.setHeader('Content-Type','application/zip')
    self.request.RESPONSE.setHeader('Content-disposition','attachment;filename=%s.zip' % self.context.getId())
    return self.zipfiles()
  
  def zipfiles(self):
    """ Zip all of the content in this location (context)"""
    from io import BytesIO
    stream = BytesIO()
    
    self.zipFilePairs(stream)
    return stream.getvalue()

  def zipFilePairs(self, fstream):
    """Return the path and file stream of all content we find here"""
    base_path = '/'.join(self.context.getPhysicalPath())+'/' # the path in the ZCatalog
    portal = component.getUtility(ISiteRoot)
    cat = getToolByName(portal,'portal_catalog')
    filepairs = []
    
    zipper = zipfile.ZipFile(fstream, 'w', zipfile.ZIP_DEFLATED)

    content = cat(path=base_path,object_provides=IZippable.__identifier__)
    for c in content:
      rel_path = c.getPath().split(base_path)[1:] or [c.getId] # the latter if the root object has an adapter
      if rel_path:
        zip_path = os.path.join(*rel_path)
        adapter = component.queryAdapter(c.getObject(),IZippable)
        stream = adapter.getZippable()
        ext = adapter.getExtension()
        zipper.writestr(zip_path+ext, stream)
    zipper.close()
import string

def fixprops(self,properties,old,new):
    """
    Do a text replace in certain properties of zwiki pages in this folder.
    
    For all zwiki pages in this folder, replace all occurrences of old
    with new in the specified property or properties (must be string
    properties). You could call this from your browser, eg like so:

    http://.../wikifolder/fixprops?properties:list=creation_time&properties:list=last_edit_time&old=Central Standard Time&new=CST

    Don't leave this method accessible to untrusted users.
    """
    if not old:
        return
    if type(properties) == type(''):
        properties = (properties,)
    # poor caching (ok)
    for page in self.pageObjects():
        for prop in properties:
            s = getattr(page,prop,'')
            if string.find(s,old) != -1:
                setattr(page,prop,string.replace(s,old,new))
                self.REQUEST.RESPONSE.write(
                    "changed %s.%s from %s to %s\n" % \
                    (page.id(),prop,s,getattr(page,prop)))

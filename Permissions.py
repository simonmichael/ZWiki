######################################################################
# ZWiki permissions

from AccessControl.Permissions import view, manage_properties, \
     add_documents_images_and_files, ftp_access
View          = view
Upload        = add_documents_images_and_files
FTPRead = FTP = ftp_access

AddWiki       = 'Zwiki: Add wikis'
Add           = 'Zwiki: Add pages'
Comment       = 'Zwiki: Add comments'
ChangeType    = 'Zwiki: Change page types'
Delete        = 'Zwiki: Delete pages'
Edit          = 'Zwiki: Edit pages'
Rename        = 'Zwiki: Rename pages'
Rate          = 'Zwiki: Rate pages'
Reparent      = 'Zwiki: Reparent pages'

AddPage = Add
Change = Edit
Append = Comment

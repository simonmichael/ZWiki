## Script (Python) "wikifolder_edit"
##parameters=title, description, choice=' Change '
##title=Edit a wikifolder
 
context.edit( title=title,
              description=description)

qst='portal_status_message=Wiki+Folder+changed.'

if choice == ' Change and View ':
    target_action = context.getTypeInfo().getActionById( 'view' )
else:
    target_action = context.getTypeInfo().getActionById( 'edit' )

context.REQUEST.RESPONSE.redirect( '%s/%s?%s' % ( context.absolute_url()
                                                , target_action
                                                , qst
                                                ) )


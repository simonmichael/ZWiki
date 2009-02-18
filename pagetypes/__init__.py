# backwards compatibility
try:
    import html
    ZwikiHtmlPageType = html.PageTypeHtml
except ImportError: pass
try:
    import moin
    ZwikiMoinPageType = moin.PageTypeMoin
except ImportError: pass
try:
    import plaintext
    ZwikiPlaintextPageType = plaintext.PageTypePlaintext
except ImportError: pass
try:
    import rst
    ZwikiRstPageType = rst.PageTypeRst
except ImportError: pass
try:
    import stx
    ZwikiStxPageType = stx.PageTypeStx
except ImportError: pass
try:
    import wwml
    ZwikiWwmlPageType = wwml.PageTypeWwml
except ImportError: pass

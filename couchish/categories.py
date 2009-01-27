import yaml, logging

log = logging.getLogger(__name__)


def accumulate_categories(cats, flatcats, prefix):
    if cats is None:
        return flatcats
    for c in cats:
        for category_key_label_tuple, subcats in c.items():
            cat_label, cat_key = category_key_label_tuple.split(',')
            dotted_key = '%s%s'%(prefix,cat_key)
            flatcats.append((dotted_key,cat_label))
            accumulate_categories(subcats, flatcats, '%s.'%dotted_key)
    return flatcats
    
def create_categories(db, categories):
    """
    Allows the use of views similar to the following.
    
    function(doc) {
      if (doc.model_type == 'tour') {
        for (c in doc.categories) {
          var segments = doc.categories[c].split('.');
          for (s in segments) {
            var S = parseInt(s)+1;
             var segment = segments.slice(0,S);
            emit(segment, doc._id);
          } 
        }
    """
    flatcats = accumulate_categories(categories,[],'')
    for key, label in flatcats:
        print 'incat',key, label
        if len(db.view('_all_docs',key=key)) == 0:
            log.debug('initialising category (label,key): (%s,%s)'%(label, key))
            print 'initialising category (label,key): (%s,%s)'%(label, key)
            db[key] = {'model_type':'category', 'label': label, 'keys': key.split('.')}

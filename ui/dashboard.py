"""Computed summaries for the interactive workspace."""
def mean_quality(mapping):
    return sum(item['score'] for item in mapping.values())/max(1,len(mapping))

def issue_rows(name,quality):
    rows=[]
    rules=[('missing','Missing','Medium','Preserve unknown values / review imputation'),
           ('invalid','Invalid format','High','Validate format'),
           ('formatting','Formatting','Low','Normalize spaces and case'),
           ('type_inconsistent','Type problem','Medium','Convert using semantic type'),
           ('category_inconsistent','Inconsistent value','Medium','Normalize categories'),
           ('outliers_flagged','Outlier','Medium','Review business context')]
    for issue in quality['issues']:
        for key,kind,severity,action in rules:
            if issue[key]: rows.append({'dataset':name,'column':issue['column'],'issue_type':kind,
                'count':issue[key],'severity':severity,'recommended_action':action})
    if quality['duplicate_rows']: rows.append({'dataset':name,'column':'(record)','issue_type':'Duplicate',
        'count':quality['duplicate_rows'],'severity':'High','recommended_action':'Remove identical records'})
    return rows

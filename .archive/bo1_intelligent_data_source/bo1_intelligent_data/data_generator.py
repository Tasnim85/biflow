from pathlib import Path
import numpy as np
import pandas as pd

def generate_data(rows=200,seed=42,directory=None):
    if rows<20: raise ValueError('Use at least 20 rows.')
    rng=np.random.default_rng(seed); ids=[f'C{i:05d}' for i in range(1,rows+1)]
    first=rng.choice(['Samar','Amine','Lina','Youssef','Nour','Adam'],rows)
    last=rng.choice(['Mansour','Ben Ali','Trabelsi','Hamdi','Karoui'],rows)
    customers=pd.DataFrame({'customer_id':ids,'first_name':first,'last_name':last,
        'email':[f'client{i}@example.com' for i in range(rows)],'phone':[f'+216{20000000+i:08d}' for i in range(rows)],
        'city':rng.choice(['Tunis','Sfax','Sousse','Paris'],rows),'age':rng.integers(18,75,rows).astype(str),
        'registration_date':[f'2025-01-{1+i%28:02d}' for i in range(rows)]})
    clients=pd.DataFrame({'client_identifier':ids,'full_name':[f'{a} {b}' for a,b in zip(first,last)],
        'email_address':customers.email.copy(),'telephone':customers.phone.copy(),'location':customers.city.copy(),
        'customer_age':customers.age.copy(),'signup_date':pd.to_datetime(customers.registration_date).dt.strftime('%d/%m/%Y')})
    clients=clients[['location','email_address','client_identifier','customer_age','telephone','signup_date','full_name']]
    count=max(30,rows//4)
    products=pd.DataFrame({'product_id':[f'P{i:04d}' for i in range(1,31)],'product_name':[f'Product {i}' for i in range(1,31)],
        'category':rng.choice(['Hardware','Software','Services'],30),'price':[f'${x:.2f}' for x in rng.uniform(5,200,30)]})
    transactions=pd.DataFrame({'transaction_id':[f'T{i:06d}' for i in range(rows*3)],'client_id':rng.choice(ids,rows*3),
        'transaction_date':['2025-02-15']*(rows*3),'amount':[f'${x:.2f}' for x in rng.uniform(5,600,rows*3)],
        'payment_method':rng.choice(['Card','Cash','Transfer'],rows*3),'product_id':rng.choice(products.product_id,rows*3)})
    employees=pd.DataFrame({'employee_id':[f'E{i:04d}' for i in range(count)],'employee_name':[f'Employee {i}' for i in range(count)],
        'department':rng.choice(['Sales','Finance','Engineering'],count),'salary':rng.integers(1500,8000,count).astype(str),
        'hire_date':['2023-03-01']*count,'email':[f'worker{i}@example.org' for i in range(count)]})
    datasets={'customers':customers,'clients_2026':clients,'transactions':transactions,'employees':employees,'products':products}
    for name,frame in datasets.items():
        for c in frame:
            frame[c]=frame[c].astype('string')
            if not (c.endswith('_id') or c=='client_identifier'):
                ix=rng.choice(frame.index,max(1,len(frame)//18),replace=False); frame.loc[ix,c]=pd.NA
            ix=rng.choice(frame.index,max(1,len(frame)//8),replace=False)
            frame.loc[ix,c]=frame.loc[ix,c].map(lambda v:f' {v} ' if pd.notna(v) else v)
            if c in ['city','location','department','category','payment_method']:
                ix=rng.choice(frame.index,max(1,len(frame)//3),replace=False); frame.loc[ix,c]=frame.loc[ix,c].str.upper()
            if 'email' in c:
                ix=rng.choice(frame.index,max(1,len(frame)//3),replace=False); frame.loc[ix,c]=frame.loc[ix,c].str.upper()
                frame.loc[1,c]='invalid-email'
            if c in ['age','customer_age']: frame.loc[2,c]='-12'; frame.loc[3,c]='210'
            if c in ['phone','telephone']: frame.loc[4,c]='123'; frame.loc[5,c]='00216 20 000 005'
            if 'date' in c: frame.loc[6,c]='31/02/2025'
        # Distinct raw forms refer to the same identifier; no case or zero stripping.
        if name=='transactions': frame.loc[7,'amount']='unknown'; frame.loc[8,'amount']='$999999.00'
        datasets[name]=pd.concat([frame,frame.iloc[:max(2,len(frame)//20)]],ignore_index=True)
    if directory:
        Path(directory).mkdir(parents=True,exist_ok=True)
        for n,df in datasets.items(): df.to_csv(Path(directory)/f'{n}.csv',index=False)
    return datasets

if __name__=='__main__': generate_data(directory=Path(__file__).parent/'data/generated')

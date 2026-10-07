"""Seeded, deliberately dirty business data with known relationships."""
from pathlib import Path
import numpy as np
import pandas as pd

def generate_data(rows=120, seed=42, directory=None):
    rng = np.random.default_rng(seed)
    ids = np.arange(1, rows + 1)
    customers = pd.DataFrame({'customer_id': ids, 'full_name': [f'Person {i}' for i in ids],
        'email': [f'person{i}@example.com' for i in ids], 'city': rng.choice(['Tunis', 'Sfax', 'Sousse'], rows),
        'signup_date': [f'2024-01-{1+i%28:02d}' for i in ids], 'age': rng.integers(18, 75, rows)})
    clients = customers.rename(columns={'customer_id':'client_id','full_name':'customer_name',
        'email':'email_address','city':'town','signup_date':'registered_on','age':'years_old'}).copy()
    clients['email_address'] = clients.email_address.str.upper().map(lambda x: f' {x} ')
    clients['registered_on'] = pd.to_datetime(clients.registered_on).dt.strftime('%d/%m/%Y')
    clients = clients[['town','email_address','client_id','years_old','registered_on','customer_name']]
    products = pd.DataFrame({'product_id':np.arange(1, 21), 'product_name':[f'Product {i}' for i in range(1,21)], 'price':[f'${x:.2f}' for x in rng.uniform(5,100,20)]})
    transactions = pd.DataFrame({'transaction_id':np.arange(1, rows*3+1), 'customer_id':rng.choice(ids,rows*3),
        'product_id':rng.integers(1,21,rows*3), 'amount':[f'${x:.2f}' for x in rng.uniform(5,500,rows*3)],
        'transaction_date':['2024-02-15']*(rows*3)})
    employees = pd.DataFrame({'employee_id':range(1,31),'employee_name':[f'Worker {i}' for i in range(1,31)],
        'department':rng.choice(['Engineering','Sales','Finance'],30),'salary':rng.integers(2000,8000,30)})
    datasets = dict(customers=customers,clients=clients,transactions=transactions,employees=employees,products=products)
    for name, frame in datasets.items():
        for column in frame.columns:
            if not column.endswith('_id'):
                frame.loc[rng.choice(frame.index,max(1,len(frame)//25),replace=False),column] = None
        datasets[name] = pd.concat([frame,frame.iloc[:3]],ignore_index=True)
    datasets['customers'].loc[5,'email'] = 'invalid-email'
    datasets['customers'].loc[6,'age'] = -5
    datasets['transactions'].loc[4,'amount'] = 'not-a-number'
    if directory:
        Path(directory).mkdir(parents=True,exist_ok=True)
        for name, frame in datasets.items(): frame.to_csv(Path(directory)/f'{name}.csv',index=False)
    return datasets

if __name__ == '__main__':
    generate_data(directory=Path(__file__).parent/'data')

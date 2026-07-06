CREATE TABLE client_beneficiaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    name_surname VARCHAR(255),
    id_number VARCHAR(255),
    cell_number VARCHAR(20),
    created_at DATETIME,
    FOREIGN KEY(client_id) REFERENCES clients(id)
);

CREATE INDEX ix_client_beneficiaries_id ON client_beneficiaries(id);
CREATE INDEX ix_client_beneficiaries_client_id ON client_beneficiaries(client_id);

select * from client_beneficiaries 

INSERT INTO client_beneficiaries (
    client_id,
    name_surname,
    id_number,
    cell_number,
    created_at
)
SELECT
    id,
    beneficiary_name_surname,
    beneficiary_id_number,
    beneficiary_cell_number,
    CURRENT_TIMESTAMP
FROM clients
WHERE beneficiary_name_surname IS NOT NULL
   OR beneficiary_id_number IS NOT NULL
   OR beneficiary_cell_number IS NOT NULL;
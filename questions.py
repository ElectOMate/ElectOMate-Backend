def match(q):
    npp = 0
    ndc = 0
    if q[0] == 'yes':
        npp += 1
    if q[0] == 'no':
        ndc += 1
    if q[1] == 'yes':
        ndc += 1
    if q[1] == 'no':
        npp += 1
    if q[2] == 'yes':
        ndc += 1
    if q[2] == 'no':
        npp += 1
    if q[3] == 'yes':
        ndc += 1
    if q[3] == 'no':
        npp += 1
    if q[4] == 'yes':
        npp += 1
    if q[4] == 'no':
        ndc += 1
    if q[5] == 'yes':
        ndc += 1
    if q[5] == 'no':
        npp += 1
    if q[6] == 'yes':
        ndc += 1
    if q[6] == 'no':
        npp += 1
    if q[7] == 'yes':
        npp += 1
    if q[7] == 'no':
        ndc += 1
    if q[8] == 'yes':
        npp += 1
    if q[8] == 'no':
        ndc += 1
    if q[9] == 'yes':
        ndc += 1
    if q[9] == 'no':
        npp += 1
    return {"New Partriotic Party": npp, "National Democratic Congress": ndc}
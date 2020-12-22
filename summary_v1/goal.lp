#program check(k).
:- query(k), cost(C,k), C <= 342.
:- query(k), cost(0,k).
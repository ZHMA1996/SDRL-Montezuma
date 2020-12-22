#program step(k).
:-at(plat1,k),move(key,k).
#program step(k).
:-at(plat1,k),move(lower_left_ladder,k).
#program step(k).
:-at(plat1,k),move(devilleft,k).
#program step(k).
:-at(lower_right_ladder,k),move(lower_left_ladder,k).
#program step(k).
:-at(lower_right_ladder,k),move(right_door,k).
#program step(k).
:-at(lower_right_ladder,k),move(key,k).
#program step(k).
:-at(devilleft,k),move(lower_left_ladder,k).
#program step(k).
:-at(key,k),picked(key,k),move(plat1,k).
#program step(k).
:-at(key,k),picked(key,k),move(devilleft,k).
#program step(k).
:-at(key,k),picked(key,k),move(lower_right_ladder,k).
#program step(k).
:-at(key,k),picked(key,k),move(right_door,k).
#program step(k).
:-at(devilleft,k),move(right_door,k).
#program step(k).
:-at(lower_left_ladder,k),picked(key,k),move(devilleft,k).
#program step(k).
:-at(lower_left_ladder,k),picked(key,k),move(plat1,k).
#program step(k).
:-at(lower_left_ladder,k),picked(key,k),move(key,k).
#program step(k).
:-at(lower_left_ladder,k),picked(key,k),move(right_door,k).
#program step(k).
:-at(devilleft,k),move(lower_right_ladder,k).
#program step(k).
:-at(plat1,k),picked(key,k),move(lower_right_ladder,k).

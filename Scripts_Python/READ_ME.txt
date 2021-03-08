Ce dossier comprend l'ensemble des scripts python codés lors du projet "Classification des fonds sous-marins par sondeur monofaisceau".

decode_and_save_EA400data_with_NME0.py : 
Ce script permet de decoder les fichiers .raw et .out fournis par l'EA400 et genere des fichiers .h5 qui sont des bases de donnees organisees en dictionnaires. Ce script est a utiliser lorsque les donnees de positionnement ont bien ete enregistrees dans les trames NME0 lors des acquisitions.


decode_and_save_EA400data_without_NME0.py : 
Ce script permet de decoder les fichiers .raw et .out fournis par l'EA400 et genere des fichiers .h5 qui sont des bases de donnees organisees en dictionnaires. Ce script est a utiliser lorsque les donnees de positionnement n'ont pas ete enregistrees dans les trames NME0 lors des acquisitions. Ainsi il est necessaire de fournir egalement en entree les fichiers de positionnement et attitude donnes par Qinsy.


analyse_data.py :
Ce script permet de traiter les fichiers .h5. Il mene les calculs suivants : positionnement des sondes, calcul de l'angle d'incidence et calcul de l'indice de retrodiffusion BS. Il contient egalement un certain nombre de fonctions de visualisation des donnees.


describe_data.py :
Ce script permet de calculer les descripteurs energetiques E1, E2, E3 et morphologique Pente. Il permet aussi de visualiser les histogrammes et de visualiser les resultats issus de la classification par K-moyennes


analyse_BS_sigma.py :
Ce script se consacre a l'analyse des donnees de retrodiffusion BS et a l'etude du parametre sigma issu de la loi de Rayleigh.


analyse_signal_E1_E2_E3.py : 
Ce script se consacre a l'analyse des descripteurs energetiques E1, E2 et E3.


analyse_BS_angles_incidences.py :
Ce script se consacre a l'etude de la retrodiffusion angulaire. Pour obtenir des comparaisons avec les courbes de reference de Jackson, ce script utilise les fichiers texte : coarse_sand, cobble, medium_sand, rock, sandy_gravel et x_fitting.

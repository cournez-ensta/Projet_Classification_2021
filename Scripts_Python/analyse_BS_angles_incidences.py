#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Librairies importee
import numpy as np
import pandas
from scipy.stats import linregress
from scipy.spatial.transform import Rotation as R
from scipy.optimize import curve_fit
from scipy.optimize import least_squares
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import glob
import os
import datetime as dt
import gdal
import rasterio
from rasterio.plot import show
import shapely.geometry
from shapely.geometry import Point, Polygon
# Autres codes python
from colormap import custom_cm


# --------------------------------------------------------------------------------#
#                      ANALYSE DES DONNEES EA400                                  #
#                                                                                 #
#   Ce code est compose d'un certain nombre de fonctions permettant de            #
#   traiter les donnees issues des acquisitions EA400 et de calculer le BS pour   #
#   tous les angles incidences et les graphes d'analyses du BS                    #
# --------------------------------------------------------------------------------#


# -------- FONCTION PERMETTANT DE CHARGER LES DONNEES H5 --------


def load_data(files):
    ''' Cette fonction permet de charger les donnees h5 de l'ensemble des fichiers dans une unqique base de donnees d
    '''
    d = {}  # ce dictionnaire contiendra l'ensemble de la base de donnée contenue dans les differents fichiers .h5
    for f in files:
        line = os.path.basename(f)[:5]

        if line not in d:
            d[line] = {}
        # - Sauvegarde des 3 DataFrame dans le dictionnaire d - #
        d[line]['data'] = pandas.read_hdf(f, key='data')
        d[line]['trajectoire'] = pandas.read_hdf(f, key='trajectoire')
        d[line]['param'] = pandas.read_hdf(f, key='param')

    return d


# ------------- CALCUL DU BS -------------

def compute_BS(d, line):
    """ Cette fonction permet de calculer le BS
    """

    # Puissance max recue
    Pr_max = d[line]['data'].loc[:, 'PowerMax']

    # Puissance emise
    Pe = d[line]['data'].loc[:, 'TransmitPower'].astype(float)

    # Range
    r = d[line]['data'].loc[:, 'Depth'].astype(float)

    # Coefficient d'absorption
    alpha = float(d[line]['param'].loc[:, 'AbsorptionCoefficient'])
    # Vitesse du son
    c = float(d[line]['param'].loc[:, 'SoundVelocity'])
    # Temps d'impulsion
    tpulse = float(d[line]['param'].loc[:, 'PulseLength'])
    # Angle de dépointage
    angle = float(d[line]['param'].loc[:, 'Angle'])
    # Angle d'incidence
    angle_incidence = d[line]['data'].loc[:, 'IncidenceAngle']
    # Longueur d'onde
    lambd = float(d[line]['param'].loc[:, 'SoundVelocity'] / d[line]['param'].loc[:, 'Frequency'])

    # Si la fréquence utilisée est le 38kHz
    if (float(d[line]['param'].loc[:, 'Frequency']) == 38000):
        # Gain de traitement
        Gain = float(d[line]['param'].loc[:, 'Gain_38'])
        # Angle solide equivalent
        psi = float(d[line]['param'].loc[:, 'EquivalentBeamAngle_38'])

    # Si la fréquence utilisée est le 200kHz
    else:
        Gain = float(d[line]['param'].loc[:, 'Gain_200'])
        psi = float(d[line]['param'].loc[:, 'EquivalentBeamAngle_200'])


    # Calcul du BS
    ### Aire pour rayon dépointé
    Aire = np.min(
        [(c * tpulse * r) / (2 * (np.sin((angle_incidence / 180) * np.pi))) * np.sqrt((4 * 10 ** (psi / 10)) / np.pi),
         (r ** 2) * 10 ** (psi / 10)], axis=0)

    # Calcul du BS
    BS = Pr_max - 10 * np.log10(Pe) + 40 * np.log10(r) + 2 * alpha * r - 10 * np.log10(
        lambd ** 2 / (16 * ((np.pi) ** 2))) - 10 * np.log10(Aire) - 2 * Gain

    # Sauvegarde du BS calcule dans le dictionnaire d
    d[line]['data'].loc[:, 'BS_calc'] = BS
    return d

# --------- CHANGE ZONE ----------------------------------

def addZone(d,line):
    """ Cette fonction permet d'identifier la zone des pings qui seront traités"""

    # Chargement des données
    data = d[line]['data']

    # Création dun tableaux pour les positions des zones
    data['Zone'] = np.zeros((data.shape[0]))

    zone1 = Polygon([[147909, 6831018], [147970, 6831058], [148045, 6830968], [147981, 6830911]])
    zone2 = Polygon([[148097, 6830111], [148039, 6830173], [148119, 6830245], [148173, 6830177]])
    zone3 = Polygon([[147665, 6829667], [147586, 6829740], [147663, 6829810], [147727, 6829746]])
    zone4 = Polygon([[147197, 6829228], [147130, 6829306], [147200, 6829366], [147258, 6829301]])
    zone5 = Polygon([[146527, 6830611], [146510, 6830712], [146694, 6830745], [146723, 6830635]])

    for index, row in data.iterrows():
        ping = Point(row['X_Beam'], row['Y_Beam'])
        if zone1.contains(ping):
            row['Zone'] = 1
        elif zone2.contains(ping):
            row['Zone'] = 2
        elif zone3.contains(ping):
            row['Zone'] = 3
        elif zone4.contains(ping):
            row['Zone'] = 4
        elif zone5.contains(ping):
            row['Zone'] = 5
        data.at[index] = row

    d[line]['data'] = data

    return d


# ------------- CALCUL DE L'ANGLE D'INCIDENCE -------------

def computeCoordsBeam(d, line, bdl, pt):
    """ Cette fonction permet de calculer les coordonnées de la tache insonifiee
    coordonnees du centre de la tâche insonifiée
    coordonnees des extremites de la tache insonifiee selon l'axe transversal au navire
    """
    # Chargement des données
    data = d[line]['data']

    # Positions et attitudes données par la centrale inertielle
    x_ins = data['X']
    y_ins = data['Y']
    z_ins = data['Height']
    pitch = data['Pitch']
    roll = data['Roll']
    yaw = data['Gyro']
    # Profondeurs données par le monofaisceau
    depth = data['Depth']
    # Angle de dépointage
    a_dep = data['Angle'][0]

    # Si la fréquence utilisée est le 38kHz
    if (float(d[line]['param'].loc[:, 'Frequency']) == 38000):
        a_ape = 21
    # Si la fréquence utilisée est le 200kHz
    else :
        a_ape = 7

    # Nombre de pings de la ligne
    nb_ping = data.shape[0]

    # Bras de levier du monofaisceau
    PSBES = np.array([bdl[2], bdl[1], bdl[0]])
    PatchTest = np.array([pt[2], pt[1], pt[0]])

    # Tableau vide pour la position des sondes
    pos_sond = np.zeros((nb_ping, 3))
    pos_sond_av = np.zeros((nb_ping, 3))
    pos_sond_ap = np.zeros((nb_ping, 3))

    for k in range(nb_ping):
        # coordonnées de la sonde dans le repére du monofaiseau
        m_sond = np.array([depth[k], 0, 0])

        # Matrice de rotation pour les angles d'installation du monofaisceau
        R_patch_test = R.from_euler('zyx', PatchTest, degrees=True)

        # Matrice de rotation avec les attitudes du bateau
        R_attitude = R.from_euler('zyx', [-(roll[k] + a_dep), pitch[k], -yaw[k]], degrees=True)
        # Matrice de rotation pour avoir la position de la tache insonifiéé
        R_attitude_av = R.from_euler('zyx', [-(roll[k] + a_dep - a_ape / 2), pitch[k], -yaw[k]], degrees=True)
        R_attitude_ap = R.from_euler('zyx', [-(roll[k] + a_dep + a_ape / 2), pitch[k], -yaw[k]], degrees=True)

        # Coordonnées de l'INS
        zyx_ins = np.array([z_ins[k], y_ins[k], x_ins[k]])

        # Coordonnées des sondes
        pos_sond[k, :] = zyx_ins + R_attitude.apply(R_patch_test.apply(m_sond) + PSBES)
        # Coordonnées de la tache insonifiée
        pos_sond_av[k, :] = zyx_ins + R_attitude_av.apply(R_patch_test.apply(m_sond) + PSBES)
        pos_sond_ap[k, :] = zyx_ins + R_attitude_ap.apply(R_patch_test.apply(m_sond) + PSBES)

    # Valeur des coordonnées des sondes et de la tâche insonifiée
    data['X_Beam'] = pos_sond[:, 2]
    data['Y_Beam'] = pos_sond[:, 1]
    data['X_closeBeam'] = pos_sond_av[:, 2]
    data['Y_closeBeam'] = pos_sond_av[:, 1]
    data['X_farBeam'] = pos_sond_ap[:, 2]
    data['Y_farBeam'] = pos_sond_ap[:, 1]

    d[line]['data'] = data

    return d

# ------------- CALCUL DE L'ANGLE D'INCIDENCE -------------

def computeIncidenceAngle(d, line, d_mnt, idzone):
    """ Cette fonction permet de calculer l'angle d'incidence à partir de la bathymetrie
    et de la position de la tache insonifiee
    """

    # Chargement des données, des coordonées de la zone et du MNT
    data = d[line]['data']
    zone = int(max(data['Zone']))
    mnt = rasterio.open(d_mnt[zone])

    # Chargement des données du MNT
    bande_1 = mnt.read(1)

    # Nombre de pngs pour la ligne
    nb_ping = data.shape[0]

    # Création d'un tableaux pour les valeurs des angles d'incidences
    angle_i = np.zeros(nb_ping)

    # Données de la posiion de la tâche insonifiée
    X_av = data['X_closeBeam']
    Y_av = data['Y_closeBeam']
    X_ap = data['X_farBeam']
    Y_ap = data['Y_farBeam']
    # Données de roulis
    roll = data['Roll']
    # Angle de dépointage
    a_dep = data['Angle'][0]

    for k in range(nb_ping):

        # On vérifie que notre zone se situe bien sur le MNT
        if int(data['Zone'][k]) == idzone:
            # Permet d'avoir position de la sonde sur le MNT
            row_av, col_av = mnt.index(X_av[k], Y_av[k])
            row_ap, col_ap = mnt.index(X_ap[k], Y_ap[k])

            # Permet d'avoir la profondeur avant et après la tâche insonifiée
            z_av = bande_1[row_av, col_av]
            z_ap = bande_1[row_ap, col_ap]

            # Calcul de la longeur de la pente autour de la tâche insonifiée
            longueur_pente = np.sqrt((X_ap[k] - X_av[k]) ** 2 + (Y_ap[k] - Y_av[k]) ** 2)
            # Calcul du dénivelé autour de la tâche insonifiée
            denivele = z_ap - z_av
            # Calcul de la pente autour de la tâche insonifiée
            p = np.arcsin(denivele / longueur_pente) * 180 / np.pi
            # Angle entre l'angle de dépointage et le roulis
            phi = a_dep - roll[k]
            # Calcul de l'angle d'incidence
            angle_i[k] = 90 - phi + p
        else:
            angle_i[k] = np.NaN

    data['IncidenceAngle'] = angle_i

    d[line]['data'] = data
    return d

# ------------- CALCUL MOYENNE DU BS -------------

def computeMeanCourb(d, line):
    """ Cette fonction permet de calculer la moyenne du BS
     tous les 1 degré si on a plus de 10 valeurs de BS
    """

    # Chargement des valeurs de BS
    BS = d[line]['data'].loc[:, 'BS_calc']
    # Chargement des valeurs des angles d'incidences
    Angle = 90 - d[line]['data'].loc[:, 'IncidenceAngle']
    # Valeurs mnimales et maximales des angles d'incidences
    a_min, a_max = (int(np.nanmin(Angle)) // 2) * 2, (int(np.nanmax(Angle)) // 2 + 1) * 2
    # Liste pour le calcul de moyenne tous les 1 degré
    l_interv = [(i, i + 1) for i in range(a_min, a_max)]
    # Liste vide pour les valeurs de moyenne
    x_mean = []
    y_mean = []
    for i in l_interv:
        subBS = BS.loc[(Angle > i[0]) & (Angle < i[1])]
        # On vérifie qu'on a plus de 10 valeurs
        if len(subBS) > 10:
            x_mean.append(i[0] + 0.5)
            y_mean.append(np.mean(10 ** (subBS / 10)))

    return  x_mean, y_mean

# ------------- CALCUL DU MODELE DE LA COURBE DU BS -------------

def BS_fitting(theta, A, B, C, alpha, beta, gamma):
    """ Cette fonction permet de calculer
    la fonction modéle de la courbe du BS
    """

    return 10 * np.log10(
        A * np.exp(-alpha * theta ** 2) + B * (np.cos(theta * np.pi / 180)) ** beta + C * np.exp(-gamma * theta ** 2))

# ------------- CALCUL ET AFFICHAGE DE LA COURBE DU BS -------------

def plotBSIncidence(d, lines, title, idzone, freq):
    """
    Cette fonction permet d'afficher et de calculer la courbe modèle de BS en fonction de l'angle d'incidence
    Elle peret aussi d'afficher les valeurs de BS et les points de moyenne
    """

    plt.figure()

    xmean_all, ymean_all = [], []

    for line in lines:
        # Appelle aux fonctions décrites précédemment
        d = computeCoordsBeam(d, line, bras_levier, patch_test)
        d = computeIncidenceAngle(d, line, d_mnt, idzone)
        d = compute_BS(d, line)
        d = addZone(d, line)

        # Calcul des points de moyenne
        xmean, ymean = computeMeanCourb(d, line)
        xmean_all += xmean
        ymean_all += ymean

        # Chargement du BS
        BS = d[line]['data'].loc[:, 'BS_calc']
        # Chargement de l'angle d'incidence
        Angle = 90 - d[line]['data'].loc[:, 'IncidenceAngle']
        # Chargement de l'angle de dépointage
        angle = d[line]['param'].loc[:, 'Angle'].values[0]
        plt.scatter(Angle, BS, marker='+', label=line + ' : ' + str(angle) + '°')


    xmean_all = np.array(xmean_all)
    xmean_all = np.concatenate((xmean_all, -xmean_all))
    ymean_all_log = 10 * np.log10(np.array(ymean_all))
    ymean_all_log = np.concatenate((ymean_all_log, ymean_all_log))

    ### Méthdde curve fit
    """
    Cette méthode permet de calculer la courbe de BS à partir du modèle
     et de la faire fitter sur les points de moyenne
    """

    # Coefficients de départ à 38kHz pour la méthode curve fit ( coefficients obtenues grâce à plusieurs essais )
    if freq == 38:
        if idzone == 1:
            coeff = (0.06085667719006585, 0.03261464631990873, 0.12884259820837032, 0.007394352347036646, 2.4726798164360764, 0.0027386494940268933) # mean

        if idzone == 2:
            coeff = (0.15163300200467683, 0.03280817845579377, 0.0004856821405936402, 0.0032894911014129625, 2.0232310042643444, 175.30759723671972) # mean

        if idzone == 3:
            coeff = (0.19497197272430525, 0.02653292357102636, 0.010251627477231032, 0.005203886790815789, 1.9987065701436662, 0.0012939545517793249) # mean

        if idzone == 4:
            coeff = (0.25897609629628265, 0.0945029825017366, -0.0021016843098315497, 0.0041608429953892976, 2.1943296313028817, 459.2233866993328) # mean

        if idzone == 5:
            coeff = (0.25756235219088336, 0.055278932979646735, -0.05710865773005725, 0.0032018944206997487, 2.3034508487562038, 0.001001267666435326) # mean
    # Coefficients de départ à 200kHz pour la méthode curve fit ( coefficients obtenues grâce à plusieurs essais )
    if freq == 200:
        if idzone == 1:
            coeff = (0.14396631670558777, 0.03627959631669168, 0.1793120696318242, 0.002388006201758988, 1.8442080723851775, 0.009409316814658567) # mean

        if idzone == 2:
            coeff = (0.22943597389545525, 0.06023162508687232, 0.0004856821405936402, 0.0033708940616808173, 1.6705761022648873, 175.307597236719722) # mean

        if idzone == 3:
            coeff = (0.4036680518457063, 0.10245538587757567, 0.10438478443666345, 0.005615436625740945, 1.831511109809131, 0.001563793955128834) # mean

        if idzone == 4:
            coeff = (1.1526938354766763, 0.21399915307423442, -0.0021016843098315497, 0.0055818407586008525, 2.1466169437855718, 459.2233866993328) # mean

        if idzone == 5:
            coeff = (0.7681139429371083, 0.13961887828549235, 0.36087560645981626, 0.011433839892358624, 2.1342923138883547, 0.002139548049543967) # mean


    # Fitting du modèle sur nos points de moyenne
    popt, pcov = curve_fit(BS_fitting, xmean_all, ymean_all_log, p0=coeff)
    angle_poly = np.arange(-80, 80, 1)
    A, B, C, alpha, beta, gamma = popt
    y_poly = BS_fitting(angle_poly, A, B, C, alpha, beta, gamma)

    # Sauvegarde des valeurs de la courbe dans des fichiers textes
    if freq == 38:
        if idzone == 1:
            np.savetxt('y_fitting_zone_1_38', y_poly)

        if idzone == 2:
            np.savetxt('y_fitting_zone_2_38', y_poly)

        if idzone == 3:
            np.savetxt('y_fitting_zone_3_38', y_poly)

        if idzone == 4:
            np.savetxt('y_fitting_zone_4_38', y_poly)

        if idzone == 5:
            np.savetxt('y_fitting_zone_5_38', y_poly)

    # Sauvegarde des valeurs de la courbe dans des fichiers textes
    if freq == 200:
        if idzone == 1:
            np.savetxt('y_fitting_zone_1_200', y_poly)

        if idzone == 2:
            np.savetxt('y_fitting_zone_2_200', y_poly)

        if idzone == 3:
            np.savetxt('y_fitting_zone_3_200', y_poly)

        if idzone == 4:
            np.savetxt('y_fitting_zone_4_200', y_poly)

        if idzone == 5:
            np.savetxt('y_fitting_zone_5_200', y_poly)


    ### Figure
    plt.scatter(xmean_all, ymean_all_log, marker='x', c='k', label='mean')
    plt.plot(angle_poly, y_poly, c='k', label='fitting')
    plt.xlim([0, 80])
    plt.ylim([-40, 5])
    plt.legend()
    plt.ylabel('Indice de rétrodiffusion (dB))')
    plt.xlabel("Angle d'incidence (degré)")
    plt.title(title)

    return None


# ------------- AFFICHAGE DES COURBES DU BS -------------

def affichage_courbe_BS_finale(freq):
    """
    Affiche les courbes de BS pour lles 5 zones
    """

    if freq == 38:
        zone_1 = np.loadtxt('y_fitting_zone_1_38')
        zone_2 = np.loadtxt('y_fitting_zone_2_38')
        zone_3 = np.loadtxt('y_fitting_zone_3_38')
        zone_4 = np.loadtxt('y_fitting_zone_4_38')
        zone_5 = np.loadtxt('y_fitting_zone_5_38')

    if freq == 200:
        zone_1 = np.loadtxt('y_fitting_zone_1_200')
        zone_2 = np.loadtxt('y_fitting_zone_2_200')
        zone_3 = np.loadtxt('y_fitting_zone_3_200')
        zone_4 = np.loadtxt('y_fitting_zone_4_200')
        zone_5 = np.loadtxt('y_fitting_zone_5_200')

    x_fitting = np.loadtxt('x_fitting')

    plt.figure()
    plt.plot(x_fitting, zone_1, label='zone 1')
    plt.plot(x_fitting, zone_2, label='zone 2')
    plt.plot(x_fitting, zone_3, label='zone 3')
    plt.plot(x_fitting, zone_4, label='zone 4')
    plt.plot(x_fitting, zone_5, label='zone 5')
    plt.xlim([0, 80])
    plt.ylim([-40, 5])
    plt.legend()
    plt.ylabel('Indice de rétrodiffusion (dB)')
    plt.xlabel("Angle d'incidence (degré)")

    return None


# ------------- AFFICHAGE DE LA COURBE DE BS ZONE 5 A 200kHz ET CELLE DE L'IFREMER -------------

def comparaison_données_ifremer():
    """
    Comparason entre nos valeurs de BS
    et celle de l'Ifremer sur la zone 5 à 200 kHz
    """

    zone_5 = np.loadtxt('y_fitting_zone_5_200', c='tab:purple')
    x_fitting = np.loadtxt('x_fitting')

    # Données ifremer
    data = np.loadtxt('fit_CR_200.txt')

    plt.figure()
    plt.plot(x_fitting, zone_5, label='zone 5', c='tab:purple')
    plt.plot(data[:, 0], data[:, 1], label='Référence', c='k')
    plt.xlim([0, 80])
    plt.ylim([-40, 5])
    plt.legend()
    plt.ylabel('Indice de rétrodiffusion (dB)')
    plt.xlabel("Angle d'incidence (degré)")

    return None


# ------------- COMPARAISON ENTR ENOS DONNEES ET CELLES DE JACKSON A 38kHz -------------

def comparaison_Jackson(nom):
    """
    Affiche les courbes de BS à 38kHz
    et les valeurs de Jackson pour le fichier en entrée
    Donne les différences entre nos valeurs de BS et celle de Jackons
    """

    # Chargement des valeurs de Jackson
    data_medium_sand = np.loadtxt('medium_sand')
    data_coarse_sand = np.loadtxt('coarse_sand')
    data_sandy_gravel = np.loadtxt('sandy_gravel')
    data_copple = np.loadtxt('cobble')
    data_rock = np.loadtxt('rock')

    x_fitting = np.loadtxt('x_fitting')
    y_fitting = np.loadtxt(nom)

    # Calcul dess différences de BS entre Jackson et nous
    diff1 = [];
    diff2 = [];
    diff3 = [];
    diff4 = [];
    diff5 = []
    temp = [y_fitting[79], y_fitting[80], y_fitting[81], y_fitting[84], y_fitting[89], y_fitting[99], y_fitting[109],
            y_fitting[129], y_fitting[149], y_fitting[159]]

    for k in range(data_rock[:, 0].shape[0]):
        diff1.append(temp[k] - data_rock[k, 1])
        diff2.append(temp[k] - data_copple[k, 1])
        diff3.append(temp[k] - data_sandy_gravel[k, 1])
        diff4.append(temp[k] - data_coarse_sand[k, 1])
        diff5.append(temp[k] - data_medium_sand[k, 1])

    print('Différences rock : ', np.mean(diff1))
    print('Différences copple : ', np.mean(diff2))
    print('Différences sandy gravel : ', np.mean(diff3))
    print('Différences coarse sand : ', np.mean(diff4))
    print('Différences medium sand : ', np.mean(diff5))

    plt.figure()
    plt.plot(x_fitting, y_fitting, c='tab:blue')
    plt.plot(data_rock[:, 0], data_rock[:, 1], 'H', label='rock', c='k')
    plt.plot(data_copple[:, 0], data_copple[:, 1], 's', label='copple', c='k')
    plt.plot(data_sandy_gravel[:, 0], data_sandy_gravel[:, 1], '*', label='sandy gravel', c='k')
    plt.plot(data_coarse_sand[:, 0], data_coarse_sand[:, 1], '+', label='coarse sand', c='k')
    plt.plot(data_medium_sand[:, 0], data_medium_sand[:, 1], 'D', label='medium sand', c='k')
    plt.legend()
    plt.xlim([0, 80])
    plt.ylim([-40, 5])
    plt.ylabel('Indice de rétrodiffusion (dB)')
    plt.xlabel("Angle d'incidence (degré)")

    return None


if __name__ == '__main__':

    plt.close('all')  # Fermer toutes les figures encore ouvertes

    # ----- VARIABLES ------
    bras_levier = [1.2565, -1.21, -1.881]  # Bras de levier x,y,z
    patch_test = [0, 0, 0]  # Patch test x,y,z

    # Chemins vers les MNT
    d_mnt = {1: './MNT/MNT_Zone1_07102020_L93.tif', 6: './MNT/MNT_Zone1_07102020_L93.tif', 2: './MNT/MNT_Zone2_07102020_L93.tif',
             3: './MNT/MNT_Zone2_07102020_L93.tif', 4: './MNT/MNT_Zone2_07102020_L93.tif',
             5: './MNT/MNT_Zone3_07102020_L93.tif'}

    # ----- CHEMINS VERS LES REPERTOIRES A 38 kHz -----

    dir_path = './fic_h5_38kHz/'  # repertoire d'entree contenant les fichiers h5
    files38_h5 = glob.glob(dir_path + '*_38kHz_data.h5')  # Ensemble des fichiers h5 à 38kHz à traiter (chemins)


    # ----- CHARGEMENT DE LA BASE DE DONNEES A 38kHz -----

    d = load_data(files38_h5)  # Données


    # ----- TRAITEMENTS ET AFFICHAGES -----

    # Affichage de la courbe de BS en fonction de l'angle d'incidence
    lines = ['L0008','L0029','L0030','L0031','L0032','L0033']
    plotBSIncidence(d,lines,'Zone 1',1, 38)

    lines = ['L0019', 'L0035', 'L0036', 'L0037', 'L0038', 'L0039']
    plotBSIncidence(d, lines, 'Zone 2', 2, 38)
    plotBSIncidence(d, lines, 'Zone 3', 3, 38)

    lines = ['L0018', 'L0035', 'L0036', 'L0038', 'L0039', 'L0135', 'L0137']
    plotBSIncidence(d, lines, 'Zone 4', 4, 38)

    lines = ['L0024','L0041','L0042','L0043','L0044','L0045']
    plotBSIncidence(d, lines,'Zone 5',5, 38)



    # ----- CHEMINS VERS LES REPERTOIRES A 200kHz -----

    dir_path = './fic_h5_200kHz/'  # repertoire d'entree contenant les fichiers h5
    files200_h5 = glob.glob(dir_path + '*_200kHz_data.h5')  # Ensemble des fichiers h5 à 200kHz à traiter (chemins)


    # ----- CHARGEMENT DE LA BASE DE DONNEES A 200kHz-----

    d = load_data(files200_h5)  # Données

    # ----- TRAITEMENTS ET AFFICHAGES -----

    # Affichage de la courbe de BS en fonction de l'angle d'incidence
    lines = ['L0008', 'L0029', 'L0030', 'L0031', 'L0032', 'L0033']
    plotBSIncidence(d, lines, 'Zone 1', 1, 200)

    lines = ['L0019', 'L0035', 'L0036', 'L0037', 'L0038', 'L0039']
    plotBSIncidence(d, lines, 'Zone 2', 2, 200)
    plotBSIncidence(d, lines, 'Zone 3', 3, 200)

    lines = ['L0018', 'L0035', 'L0036', 'L0038', 'L0039', 'L0135', 'L0137']
    plotBSIncidence(d, lines, 'Zone 4', 4, 200)

    lines = ['L0024', 'L0041', 'L0042', 'L0043', 'L0044', 'L0045']
    plotBSIncidence(d, lines, 'Zone 5', 5, 200)

    # ----- ANALYSES DES COURBES DE BS OBTENUES -----

    # Affichage des courbes de BS
    frequence =38
    affichage_courbe_BS_finale(frequence)

    # Affichage courbe zone 5 200kHz et données Ifremer
    comparaison_données_ifremer()

    # Comparaison nos données et celle de Jackson
    # SEULEMENT A 38kHz
    nom_fichier = 'y_ftting_zone_1_38'
    comparaison_Jackson(nom_fichier)

    plt.show()


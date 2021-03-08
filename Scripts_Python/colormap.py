# -*- coding: utf-8 -*-
# Auteur : Marceau MICHEL

""" Colormap de Movies 3D de l'IFREMER
    copyright Laurent Berger 

    conversion en matplotlib
"""
import numpy as np
import matplotlib


def custom_cm():
    color_data = np.array(((1, 1, 1),
                           (0.863305330276489, 0.931092441082001, 0.968627452850342),
                           (0.726610660552979, 0.862184882164002, 0.937254905700684),
                           (0.589915990829468, 0.793277323246002, 0.905882358551025),
                           (0.453221291303635, 0.724369764328003, 0.874509811401367),
                           (0.316526621580124, 0.655462205410004, 0.843137264251709),
                           (0.179831936955452, 0.586554646492004, 0.811764717102051),
                           (0.0431372560560703, 0.517647087574005, 0.780392169952393),
                           (0.0404411777853966, 0.516421616077423, 0.731617689132690),
                           (0.0377450995147228, 0.515196084976196, 0.682843148708344),
                           (0.0350490212440491, 0.513970613479614, 0.634068608283997),
                           (0.0323529429733753, 0.512745141983032, 0.585294127464294),
                           (0.0296568628400564, 0.511519610881805, 0.536519646644592),
                           (0.0269607845693827, 0.510294139385223, 0.487745106220245),
                           (0.0242647062987089, 0.509068667888641, 0.438970595598221),
                           (0.0215686280280352, 0.507843136787415, 0.390196084976196),
                           (0.0188725497573614, 0.506617665290833, 0.341421574354172),
                           (0.0161764714866877, 0.505392193794251, 0.292647063732147),
                           (0.0134803922846913, 0.504166662693024, 0.243872553110123),
                           (0.0107843140140176, 0.502941191196442, 0.195098042488098),
                           (0.00808823574334383, 0.501715719699860, 0.146323531866074),
                           (0.00539215700700879, 0.500490188598633, 0.0975490212440491),
                           (0.00269607850350440, 0.499264717102051, 0.0487745106220245),
                           (0, 0.498039215803146, 0),
                           (0.0625000000000000, 0.529411792755127, 0),
                           (0.125000000000000, 0.560784339904785, 0),
                           (0.187500000000000, 0.592156887054443, 0),
                           (0.250000000000000, 0.623529434204102, 0),
                           (0.312500000000000, 0.654901981353760, 0),
                           (0.375000000000000, 0.686274528503418, 0),
                           (0.437500000000000, 0.717647075653076, 0),
                           (0.500000000000000, 0.749019622802734, 0),
                           (0.562500000000000, 0.780392169952393, 0),
                           (0.625000000000000, 0.811764717102051, 0),
                           (0.687500000000000, 0.843137264251709, 0),
                           (0.750000000000000, 0.874509811401367, 0),
                           (0.812500000000000, 0.905882358551025, 0),
                           (0.875000000000000, 0.937254905700684, 0),
                           (0.937500000000000, 0.968627452850342, 0),
                           (1, 1, 0),
                           (1, 0.937500000000000, 0),
                           (1, 0.875000000000000, 0),
                           (1, 0.812500000000000, 0),
                           (1, 0.750000000000000, 0),
                           (1, 0.687500000000000, 0),
                           (1, 0.625000000000000, 0),
                           (1, 0.562500000000000, 0),
                           (1, 0.500000000000000, 0),
                           (1, 0.437500000000000, 0),
                           (1, 0.375000000000000, 0),
                           (1, 0.312500000000000, 0),
                           (1, 0.250000000000000, 0),
                           (1, 0.187500000000000, 0),
                           (1, 0.125000000000000, 0),
                           (1, 0.0625000000000000, 0),
                           (1, 0, 0),
                           (0.937500000000000, 0, 0),
                           (0.875000000000000, 0, 0),
                           (0.812500000000000, 0, 0),
                           (0.750000000000000, 0, 0),
                           (0.687500000000000, 0, 0),
                           (0.625000000000000, 0, 0),
                           (0.562500000000000, 0, 0),
                           (0.500000000000000, 0, 0)))

    # Création de la colormap
    color_dict = {}

    n = color_data.shape[0]
    r = np.arange(n) / float(n - 1)
    r.shape = (n, 1)

    red_data = color_data[:, 0].reshape((n, 1))
    green_data = color_data[:, 1].reshape((n, 1))
    blue_data = color_data[:, 2].reshape((n, 1))

    color_dict['red'] = np.hstack((r, red_data, red_data))
    color_dict['green'] = np.hstack((r, green_data, green_data))
    color_dict['blue'] = np.hstack((r, blue_data, blue_data))

    movies3D = matplotlib.colors.LinearSegmentedColormap('movies3D', color_dict, 1024)
    return movies3D

'''
This file is dedicated to the navigation bar at the top of the web application.
Its main component is the Navbar function that instantiates the navigation bar.
'''

# ------------------------------------------------------------------------------
# Imports

import dash_bootstrap_components as dbc


# ------------------------------------------------------------------------------
# Content

def Navbar():

    navbar = dbc.NavbarSimple(
                              children = [
                                          dbc.DropdownMenu(
                                                           nav = True,
                                                           in_navbar = True,
                                                           label = 'Tableaux de bord',
                                                           children = [
                                                                       dbc.DropdownMenuItem('Alertes et Infrastructures',
                                                                                            href = 'alerts'),

                                                                       dbc.DropdownMenuItem('Niveaux de Risque',
                                                                                            href = 'risks')
                                                                       ],
                                                            ),
                                          ],
                              brand = 'À propos',
                              brand_href = '/home',
                              sticky = 'top'
                              )

    return navbar

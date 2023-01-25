# Pokedex class helper to instantiate pokemons in trainer's team
class DexSlot:
	def __init__(self, num, species, elements, base_stats):
		self.num = num
		self.species = species
		self.elements = elements
		self.base_stats = base_stats

# All Gen1 pokemon, types, base stats, etc
pokedex_list = {
    "BULBASAUR" : DexSlot(1,"Bulbasaur",["GRASS","POISON"],[45,49,49,65,65,45]),
    "IVYSAUR" : DexSlot(2,"Ivysaur",["GRASS","POISON"],[60,62,63,80,80,60]),
    "VENUSAUR" : DexSlot(3,"Venusaur",["GRASS","POISON"],[80,82,83,100,100,80]),
    "CHARMANDER" : DexSlot(4,"Charmander",["FIRE"],[39,52,43,50,50,65]),
    "CHARMELEON" : DexSlot(5,"Charmeleon",["FIRE"],[58,64,58,65,65,80]),
    "CHARIZARD" : DexSlot(6,"Charizard",["FIRE","FLYING"],[78,84,78,85,85,100]),
    "SQUIRTLE" : DexSlot(7,"Squirtle",["WATER"],[44,48,65,50,50,43]),
    "WARTORTLE" : DexSlot(8,"Wartortle",["WATER"],[59,63,80,65,65,58]),
    "BLASTOISE" : DexSlot(9,"Blastoise",["WATER"],[79,83,100,85,85,78]),
    "CATERPIE" : DexSlot(10,"Caterpie",["BUG"],[45,30,35,20,20,45]),
    "METAPOD" : DexSlot(11,"Metapod",["BUG"],[50,20,55,25,25,30]),
    "BUTTERFREE" : DexSlot(12,"Butterfree",["BUG","FLYING"],[60,45,50,80,80,70]),
    "WEEDLE" : DexSlot(13,"Weedle",["BUG","POISON"],[40,35,30,20,20,50]),
    "KAKUNA" : DexSlot(14,"Kakuna",["BUG","POISON"],[45,25,50,25,25,35]),
    "BEEDRILL" : DexSlot(15,"Beedrill",["BUG","POISON"],[65,80,40,45,45,75]),
    "PIDGEY" : DexSlot(16,"Pidgey",["NORMAL","FLYING"],[40,45,40,35,35,56]),
    "PIDGEOTTO" : DexSlot(17,"Pidgeotto",["NORMAL","FLYING"],[63,60,55,50,50,71]),
    "PIDGEOT" : DexSlot(18,"Pidgeot",["NORMAL","FLYING"],[83,80,75,70,70,91]),
    "RATTATA" : DexSlot(19,"Rattata",["NORMAL"],[30,56,35,25,25,72]),
    "RATICATE" : DexSlot(20,"Raticate",["NORMAL"],[55,81,60,50,50,97]),
    "SPEAROW" : DexSlot(21,"Spearow",["NORMAL","FLYING"],[40,60,30,31,31,70]),
    "FEAROW" : DexSlot(22,"Fearow",["NORMAL","FLYING"],[65,90,65,61,61,100]),
    "EKANS" : DexSlot(23,"Ekans",["POISON"],[35,60,44,40,40,55]),
    "ARBOK" : DexSlot(24,"Arbok",["POISON"],[60,85,69,65,65,80]),
    "PIKACHU" : DexSlot(25,"Pikachu",["ELECTRIC"],[35,55,30,50,50,90]),
    "RAICHU" : DexSlot(26,"Raichu",["ELECTRIC"],[60,90,55,90,90,110]),
    "SANDSHREW" : DexSlot(27,"Sandshrew",["GROUND"],[50,75,85,30,30,40]),
    "SANDSLASH" : DexSlot(28,"Sandslash",["GROUND"],[75,100,110,55,55,65]),
    "NIDORANF" : DexSlot(29,"Nidoran-F",["POISON"],[55,47,52,40,40,41]),
    "NIDORINA" : DexSlot(30,"Nidorina",["POISON"],[70,62,67,55,55,56]),
    "NIDOQUEEN" : DexSlot(31,"Nidoqueen",["POISON","GROUND"],[90,82,87,75,75,76]),
    "NIDORANM" : DexSlot(32,"Nidoran-M",["POISON"],[46,57,40,40,40,50]),
    "NIDORINO" : DexSlot(33,"Nidorino",["POISON"],[61,72,57,55,55,65]),
    "NIDOKING" : DexSlot(34,"Nidoking",["POISON","GROUND"],[81,92,77,75,75,85]),
    "CLEFAIRY" : DexSlot(35,"Clefairy",["NORMAL"],[70,45,48,60,60,35]),
    "CLEFABLE" : DexSlot(36,"Clefable",["NORMAL"],[95,70,73,85,85,60]),
    "VULPIX" : DexSlot(37,"Vulpix",["FIRE"],[38,41,40,65,65,65]),
    "NINETALES" : DexSlot(38,"Ninetales",["FIRE"],[73,76,75,100,100,100]),
    "JIGGLYPUFF" : DexSlot(39,"Jigglypuff",["NORMAL"],[115,45,20,25,25,20]),
    "WIGGLYTUFF" : DexSlot(40,"Wigglytuff",["NORMAL"],[140,70,45,50,50,45]),
    "ZUBAT" : DexSlot(41,"Zubat",["POISON","FLYING"],[40,45,35,40,40,55]),
    "GOLBAT" : DexSlot(42,"Golbat",["POISON","FLYING"],[75,80,70,75,75,90]),
    "ODDISH" : DexSlot(43,"Oddish",["GRASS","POISON"],[45,50,55,75,75,30]),
    "GLOOM" : DexSlot(44,"Gloom",["GRASS","POISON"],[60,65,70,85,85,40]),
    "VILEPLUME" : DexSlot(45,"Vileplume",["GRASS","POISON"],[75,80,85,100,100,50]),
    "PARAS" : DexSlot(46,"Paras",["BUG","GRASS"],[35,70,55,55,55,25]),
    "PARASECT" : DexSlot(47,"Parasect",["BUG","GRASS"],[60,95,80,80,80,30]),
    "VENONAT" : DexSlot(48,"Venonat",["BUG","POISON"],[60,55,50,40,40,45]),
    "VENOMOTH" : DexSlot(49,"Venomoth",["BUG","POISON"],[70,65,60,90,90,90]),
    "DIGLETT" : DexSlot(50,"Diglett",["GROUND"],[10,55,25,45,45,95]),
    "DUGTRIO" : DexSlot(51,"Dugtrio",["GROUND"],[35,80,50,70,70,120]),
    "MEOWTH" : DexSlot(52,"Meowth",["NORMAL"],[40,45,35,40,40,90]),
    "PERSIAN" : DexSlot(53,"Persian",["NORMAL"],[65,70,60,65,65,115]),
    "PSYDUCK" : DexSlot(54,"Psyduck",["WATER"],[50,52,48,50,50,55]),
    "GOLDUCK" : DexSlot(55,"Golduck",["WATER"],[80,82,78,80,80,85]),
    "MANKEY" : DexSlot(56,"Mankey",["FIGHTING"],[40,80,35,35,35,70]),
    "PRIMEAPE" : DexSlot(57,"Primeape",["FIGHTING"],[65,105,60,60,60,95]),
    "GROWLITHE" : DexSlot(58,"Growlithe",["FIRE"],[55,70,45,50,50,60]),
    "ARCANINE" : DexSlot(59,"Arcanine",["FIRE"],[90,110,80,80,80,95]),
    "POLIWAG" : DexSlot(60,"Poliwag",["WATER"],[40,50,40,40,40,90]),
    "POLIWHIRL" : DexSlot(61,"Poliwhirl",["WATER"],[65,65,65,50,50,90]),
    "POLIWRATH" : DexSlot(62,"Poliwrath",["WATER","FIGHTING"],[90,85,95,70,70,70]),
    "ABRA" : DexSlot(63,"Abra",["PSYCHIC"],[25,20,15,105,105,90]),
    "KADABRA" : DexSlot(64,"Kadabra",["PSYCHIC"],[40,35,30,120,120,105]),
    "ALAKAZAM" : DexSlot(65,"Alakazam",["PSYCHIC"],[55,50,45,135,135,120]),
    "MACHOP" : DexSlot(66,"Machop",["FIGHTING"],[70,80,50,35,35,35]),
    "MACHOKE" : DexSlot(67,"Machoke",["FIGHTING"],[80,100,70,50,50,45]),
    "MACHAMP" : DexSlot(68,"Machamp",["FIGHTING"],[90,130,80,65,65,55]),
    "BELLSPROUT" : DexSlot(69,"Bellsprout",["GRASS","POISON"],[50,75,35,70,70,40]),
    "WEEPINBELL" : DexSlot(70,"Weepinbell",["GRASS","POISON"],[65,90,50,85,85,55]),
    "VICTREEBEL" : DexSlot(71,"Victreebel",["GRASS","POISON"],[80,105,65,100,100,70]),
    "TENTACOOL" : DexSlot(72,"Tentacool",["WATER","POISON"],[40,40,35,100,100,70]),
    "TENTACRUEL" : DexSlot(73,"Tentacruel",["WATER","POISON"],[80,70,65,120,120,100]),
    "GEODUDE" : DexSlot(74,"Geodude",["ROCK","GROUND"],[40,80,100,30,30,20]),
    "GRAVELER" : DexSlot(75,"Graveler",["ROCK","GROUND"],[55,95,115,45,45,35]),
    "GOLEM" : DexSlot(76,"Golem",["ROCK","GROUND"],[80,110,130,55,55,45]),
    "PONYTA" : DexSlot(77,"Ponyta",["FIRE"],[50,85,55,65,65,90]),
    "RAPIDASH" : DexSlot(78,"Rapidash",["FIRE"],[65,100,70,80,80,105]),
    "SLOWPOKE" : DexSlot(79,"Slowpoke",["WATER","PSYCHIC"],[90,65,65,40,40,15]),
    "SLOWBRO" : DexSlot(80,"Slowbro",["WATER","PSYCHIC"],[95,75,110,80,80,30]),
    "MAGNEMITE" : DexSlot(81,"Magnemite",["ELECTRIC"],[25,35,70,95,95,45]),
    "MAGNETON" : DexSlot(82,"Magneton",["ELECTRIC"],[50,60,95,120,120,70]),
    "FARFETCH\'D" : DexSlot(83,"Farfetch'd",["NORMAL","FLYING"],[52,65,55,58,58,60]),
    "DODUO" : DexSlot(84,"Doduo",["NORMAL","FLYING"],[35,85,45,35,35,75]),
    "DODRIO" : DexSlot(85,"Dodrio",["NORMAL","FLYING"],[60,110,70,60,60,100]),
    "SEEL" : DexSlot(86,"Seel",["WATER"],[65,45,55,70,70,45]),
    "DEWGONG" : DexSlot(87,"Dewgong",["WATER","ICE"],[90,70,80,95,95,70]),
    "GRIMER" : DexSlot(88,"Grimer",["POISON"],[80,80,50,40,40,25]),
    "MUK" : DexSlot(89,"Muk",["POISON"],[105,105,75,65,65,50]),
    "SHELLDER" : DexSlot(90,"Shellder",["WATER"],[30,65,100,45,45,40]),
    "CLOYSTER" : DexSlot(91,"Cloyster",["WATER","ICE"],[50,95,180,85,85,70]),
    "GASTLY" : DexSlot(92,"Gastly",["GHOST","POISON"],[30,35,30,100,100,80]),
    "HAUNTER" : DexSlot(93,"Haunter",["GHOST","POISON"],[45,50,45,115,115,95]),
    "GENGAR" : DexSlot(94,"Gengar",["GHOST","POISON"],[60,65,60,130,130,110]),
    "ONIX" : DexSlot(95,"Onix",["ROCK","GROUND"],[35,45,160,30,30,70]),
    "DROWZEE" : DexSlot(96,"Drowzee",["PSYCHIC"],[60,48,45,90,90,42]),
    "HYPNO" : DexSlot(97,"Hypno",["PSYCHIC"],[85,73,70,115,115,67]),
    "KRABBY" : DexSlot(98,"Krabby",["WATER"],[30,105,90,25,25,50]),
    "KINGLER" : DexSlot(99,"Kingler",["WATER"],[55,130,115,50,50,75]),
    "VOLTORB" : DexSlot(100,"Voltorb",["ELECTRIC"],[40,30,50,55,55,100]),
    "ELECTRODE" : DexSlot(101,"Electrode",["ELECTRIC"],[60,50,70,80,80,140]),
    "EXEGGCUTE" : DexSlot(102,"Exeggcute",["GRASS","PSYCHIC"],[60,40,80,60,60,40]),
    "EXEGGUTOR" : DexSlot(103,"Exeggutor",["GRASS","PSYCHIC"],[95,95,85,125,125,55]),
    "CUBONE" : DexSlot(104,"Cubone",["GROUND"],[50,50,95,40,40,35]),
    "MAROWAK" : DexSlot(105,"Marowak",["GROUND"],[60,80,110,50,50,45]),
    "HITMONLEE" : DexSlot(106,"Hitmonlee",["FIGHTING"],[50,120,53,35,35,87]),
    "HITMONCHAN" : DexSlot(107,"Hitmonchan",["FIGHTING"],[50,105,79,35,35,76]),
    "LICKITUNG" : DexSlot(108,"Lickitung",["NORMAL"],[90,55,75,60,60,30]),
    "KOFFING" : DexSlot(109,"Koffing",["POISON"],[40,65,95,60,60,35]),
    "WEEZING" : DexSlot(110,"Weezing",["POISON"],[65,90,120,85,85,60]),
    "RHYHORN" : DexSlot(111,"Rhyhorn",["GROUND","ROCK"],[80,85,95,30,30,25]),
    "RHYDON" : DexSlot(112,"Rhydon",["GROUND","ROCK"],[105,130,120,45,45,40]),
    "CHANSEY" : DexSlot(113,"Chansey",["NORMAL"],[250,5,5,105,105,50]),
    "TANGELA" : DexSlot(114,"Tangela",["GRASS"],[65,55,115,100,100,60]),
    "KANGASKHAN" : DexSlot(115,"Kangaskhan",["NORMAL"],[105,95,80,40,40,90]),
    "HORSEA" : DexSlot(116,"Horsea",["WATER"],[30,40,70,70,70,60]),
    "SEADRA" : DexSlot(117,"Seadra",["WATER"],[55,65,95,95,95,85]),
    "GOLDEEN" : DexSlot(118,"Goldeen",["WATER"],[45,67,60,50,50,63]),
    "SEAKING" : DexSlot(119,"Seaking",["WATER"],[80,92,65,80,80,68]),
    "STARYU" : DexSlot(120,"Staryu",["WATER"],[30,45,55,70,70,85]),
    "STARMIE" : DexSlot(121,"Starmie",["WATER","PSYCHIC"],[60,75,85,100,100,115]),
    "MRMIME" : DexSlot(122,"Mr. Mime",["PSYCHIC"],[40,45,65,100,100,90]),
    "SCYTHER" : DexSlot(123,"Scyther",["BUG","FLYING"],[70,110,80,55,55,105]),
    "JYNX" : DexSlot(124,"Jynx",["ICE","PSYCHIC"],[65,50,35,95,95,95]),
    "ELECTABUZZ" : DexSlot(125,"Electabuzz",["ELECTRIC"],[65,83,57,85,85,105]),
    "MAGMAR" : DexSlot(126,"Magmar",["FIRE"],[65,95,57,85,85,93]),
    "PINSIR" : DexSlot(127,"Pinsir",["BUG"],[65,125,100,55,55,85]),
    "TAUROS" : DexSlot(128,"Tauros",["NORMAL"],[75,100,95,70,70,110]),
    "MAGIKARP" : DexSlot(129,"Magikarp",["WATER"],[20,10,55,20,20,80]),
    "GYARADOS" : DexSlot(130,"Gyarados",["WATER","FLYING"],[95,125,79,100,100,81]),
    "LAPRAS" : DexSlot(131,"Lapras",["WATER","ICE"],[130,85,80,95,95,60]),
    "DITTO" : DexSlot(132,"Ditto",["NORMAL"],[48,48,48,48,48,48]),
    "EEVEE" : DexSlot(133,"Eevee",["NORMAL"],[55,55,50,65,65,55]),
    "VAPOREON" : DexSlot(134,"Vaporeon",["WATER"],[130,65,60,110,110,65]),
    "JOLTEON" : DexSlot(135,"Jolteon",["ELECTRIC"],[65,65,60,110,110,130]),
    "FLAREON" : DexSlot(136,"Flareon",["FIRE"],[65,130,60,110,110,65]),
    "PORYGON" : DexSlot(137,"Porygon",["NORMAL"],[65,60,70,75,75,40]),
    "OMANYTE" : DexSlot(138,"Omanyte",["ROCK","WATER"],[35,40,100,90,90,35]),
    "OMASTAR" : DexSlot(139,"Omastar",["ROCK","WATER"],[70,60,125,115,115,55]),
    "KABUTO" : DexSlot(140,"Kabuto",["ROCK","WATER"],[30,80,90,45,45,55]),
    "KABUTOPS" : DexSlot(141,"Kabutops",["ROCK","WATER"],[60,115,105,70,70,80]),
    "AERODACTYL" : DexSlot(142,"Aerodactyl",["ROCK","FLYING"],[80,105,65,60,60,130]),
    "SNORLAX" : DexSlot(143,"Snorlax",["NORMAL"],[160,110,65,65,65,30]),
    "ARTICUNO" : DexSlot(144,"Articuno",["ICE","FLYING"],[90,85,100,125,125,85]),
    "ZAPDOS" : DexSlot(145,"Zapdos",["ELECTRIC","FLYING"],[90,90,85,125,125,100]),
    "MOLTRES" : DexSlot(146,"Moltres",["FIRE","FLYING"],[90,100,90,125,125,90]),
    "DRATINI" : DexSlot(147,"Dratini",["DRAGON"],[41,64,45,50,50,50]),
    "DRAGONAIR" : DexSlot(148,"Dragonair",["DRAGON"],[61,84,65,70,70,70]),
    "DRAGONITE" : DexSlot(149,"Dragonite",["DRAGON","FLYING"],[91,134,95,100,100,80]),
    "MEWTWO" : DexSlot(150,"Mewtwo",["PSYCHIC"],[106,110,90,154,154,130]),
    "MEW" : DexSlot(151,"Mew",["PSYCHIC"],[100,100,100,100,100,100]),
}
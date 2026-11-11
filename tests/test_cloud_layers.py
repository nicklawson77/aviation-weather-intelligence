from cloud_layers import Layer, ceiling_ft, blend_layers, metar_ceiling_adjustment

def test_categories():
    assert Layer(15,3000).category=="FEW"
    assert Layer(50,3000).category=="SCT"
    assert Layer(80,1500).category=="BKN"
    assert Layer(98,600).category=="OVC"

def test_ceiling():
    assert ceiling_ft([Layer(30,800),Layer(80,2000),Layer(99,4000)])==2000
    assert ceiling_ft([Layer(25,800),Layer(40,2000)]) is None

def test_blend():
    layers=blend_layers({"GFS":[Layer(80,1500)],"ICON":[Layer(60,1700)]})
    assert len(layers)==1
    assert layers[0]["layer"].base_ft_agl==1600
    assert layers[0]["models_reporting"]==2

def test_adjustment():
    assert metar_ceiling_adjustment(None,900,0) is None
    assert metar_ceiling_adjustment(3000,1000,6)==3000
    assert metar_ceiling_adjustment(3000,1000,0)<3000

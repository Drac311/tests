#!/usr/bin/env python3
"""Genera el proyecto Godot 'Ceniza' en el directorio actual.
Uso: python setup.py
Compatible: Windows / macOS / Linux, Python 3.8+.
"""
from pathlib import Path

ARCHIVOS = {}

ARCHIVOS["project.godot"] = r"""; Engine configuration file.
config_version=5

[application]
config/name="Ceniza"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.3", "Forward Plus")

[physics]
common/physics_ticks_per_second=60
common/physics_interpolation=true

[rendering]
renderer/rendering_method="forward_plus"
anti_aliasing/quality/msaa_3d=1
"""

ARCHIVOS["main.tscn"] = r"""[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/Main.gd" id="1"]

[node name="Main" type="Node3D"]
script = ExtResource("1")
"""

ARCHIVOS["scripts/RutaHelice.gd"] = r"""class_name RutaHelice
extends Node3D

@export var radio: float = 55.0
@export var vueltas: float = 3.0
@export var descenso: float = 80.0
@export var ancho: float = 12.0
@export var segmentos_por_vuelta: int = 72
@export var num_saltos: int = 6
@export var altura_salto: float = 1.4

var longitud_total: float = 0.0
var _pts: PackedVector3Array
var _tan: PackedVector3Array
var _lat: PackedVector3Array
var _n: int = 0

func _ready() -> void:
	_construir()
	_malla()
	_colision()

func _construir() -> void:
	_n = int(vueltas * segmentos_por_vuelta)
	_pts.resize(_n + 1)
	var saltos: Array[int] = []
	for k in num_saltos:
		saltos.append(int((float(k) + 0.5) / float(num_saltos) * float(_n)))
	for i in _n + 1:
		var t := float(i) / float(_n)
		var ang := t * TAU * vueltas
		var p := Vector3(cos(ang) * radio, -descenso * t, sin(ang) * radio)
		p.y += sin(t * 40.0) * 0.35 + cos(t * 91.0) * 0.15
		for idx in saltos:
			var d: int = i - idx
			if d >= 0 and d < 7:
				p.y += altura_salto * sin((1.0 - float(d) / 7.0) * PI)
		_pts[i] = p
	_tan.resize(_n + 1)
	_lat.resize(_n + 1)
	for i in _n + 1:
		var a := maxi(0, i - 1)
		var b := mini(_n, i + 1)
		var tv := _pts[b] - _pts[a]
		if tv.length_squared() < 0.0001: tv = Vector3.FORWARD
		_tan[i] = tv.normalized()
		var lv := _tan[i].cross(Vector3.UP)
		if lv.length_squared() < 0.0001: lv = Vector3.RIGHT
		_lat[i] = lv.normalized()
	longitud_total = 0.0
	for i in _n:
		longitud_total += _pts[i].distance_to(_pts[i + 1])

func _malla() -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in _n:
		var a0 := _pts[i] - _lat[i] * ancho * 0.5
		var b0 := _pts[i] + _lat[i] * ancho * 0.5
		var a1 := _pts[i + 1] - _lat[i + 1] * ancho * 0.5
		var b1 := _pts[i + 1] + _lat[i + 1] * ancho * 0.5
		st.set_normal(Vector3.UP); st.add_vertex(a0)
		st.set_normal(Vector3.UP); st.add_vertex(a1)
		st.set_normal(Vector3.UP); st.add_vertex(b0)
		st.set_normal(Vector3.UP); st.add_vertex(b0)
		st.set_normal(Vector3.UP); st.add_vertex(a1)
		st.set_normal(Vector3.UP); st.add_vertex(b1)
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.24, 0.20, 0.18)
	mat.roughness = 0.95
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.material_override = mat
	add_child(mi)

func _colision() -> void:
	var caras := PackedVector3Array()
	for i in _n:
		var a0 := _pts[i] - _lat[i] * ancho * 0.5
		var b0 := _pts[i] + _lat[i] * ancho * 0.5
		var a1 := _pts[i + 1] - _lat[i + 1] * ancho * 0.5
		var b1 := _pts[i + 1] + _lat[i + 1] * ancho * 0.5
		caras.append_array([a0, a1, b0, b0, a1, b1])
	var sb := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var shape := ConcavePolygonShape3D.new()
	shape.set_faces(caras)
	cs.shape = shape
	sb.add_child(cs)
	add_child(sb)

func punto_en_t(metros: float) -> Vector3:
	if _n == 0: return Vector3.ZERO
	var t := clampf(metros / maxf(0.001, longitud_total), 0.0, 1.0)
	var f := t * float(_n)
	var i := int(f)
	var j := mini(i + 1, _n)
	return _pts[i].lerp(_pts[j], f - float(i))

func t_cercano(pos: Vector3) -> float:
	if _n == 0: return 0.0
	var best := 0
	var best_d := INF
	var step := maxi(1, _n / 150)
	for i in range(0, _n + 1, step):
		var d := pos.distance_squared_to(_pts[i])
		if d < best_d:
			best_d = d
			best = i
	return (float(best) / float(_n)) * longitud_total
"""

ARCHIVOS["scripts/MotoCeniza.gd"] = r"""class_name MotoCeniza
extends VehicleBody3D

signal aterrizaje(impacto: float)
signal choque()
signal surco_creado(pos: Vector3, dir: Vector3, fuerza: float)

@export var fuerza_motor: float = 900.0
@export var fuerza_freno: float = 8.0
@export var giro_max: float = 0.55
@export var velocidad_giro: float = 7.0
@export var retorno_giro: float = 10.0
@export var reduccion_giro: float = 0.55
@export var par_estabilizacion: float = 8.0
@export var intervalo_surco: float = 0.12
@export var desliz_minimo: float = 2.5

var rueda_trasera: VehicleWheel3D
var rueda_delantera: VehicleWheel3D
var _giro_actual: float = 0.0
var _en_suelo_prev: bool = false
var _timer_surco: float = 0.0
var _pico_vy: float = 0.0
var _tiempo_aire: float = 0.0

func _ready() -> void:
	mass = 180.0
	center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	center_of_mass = Vector3(0.0, -0.35, 0.0)
	continuous_cd = true
	can_sleep = false
	linear_damp = 0.05
	angular_damp = 0.6

	var cuerpo := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(0.55, 0.65, 1.75)
	cuerpo.shape = box
	add_child(cuerpo)

	rueda_trasera = _crear_rueda(Vector3(0.0, -0.38, 0.62), true, false)
	rueda_delantera = _crear_rueda(Vector3(0.0, -0.38, -0.62), false, true)

	var malla := MeshInstance3D.new()
	var cubo := BoxMesh.new()
	cubo.size = Vector3(0.5, 0.6, 1.6)
	malla.mesh = cubo
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.85, 0.30, 0.08)
	malla.material_override = mat
	add_child(malla)

func _crear_rueda(pos: Vector3, traccion: bool, direccion: bool) -> VehicleWheel3D:
	var w := VehicleWheel3D.new()
	w.position = pos
	w.wheel_radius = 0.30
	w.wheel_rest_length = 0.25
	w.suspension_travel = 0.18
	w.suspension_stiffness = 45.0
	w.suspension_max_force = 6000.0
	w.damping_compression = 1.5
	w.damping_relaxation = 2.0
	w.wheel_friction_slip = 2.0
	w.use_as_traction = traccion
	w.use_as_steering = direccion
	add_child(w)
	return w

func _physics_process(delta: float) -> void:
	_procesar_input(delta)
	_detectar_aterrizaje(delta)
	_esculpir_surco(delta)
	_estabilizar()

func _procesar_input(delta: float) -> void:
	var acel := Input.get_action_strength("acelerar")
	var fren := Input.get_action_strength("frenar")
	var giro_in := Input.get_action_strength("girar_der") - Input.get_action_strength("girar_izq")
	var v := linear_velocity.length()
	var factor := clampf(1.0 - v / 40.0 * reduccion_giro, 0.35, 1.0)
	if absf(giro_in) > 0.05:
		_giro_actual = move_toward(_giro_actual, giro_in * giro_max * factor, velocidad_giro * delta)
	else:
		_giro_actual = move_toward(_giro_actual, 0.0, retorno_giro * delta)
	steering = _giro_actual
	engine_force = acel * fuerza_motor
	brake = fren * fuerza_freno
	if fren > 0.1 and v < 3.0:
		engine_force = -fren * fuerza_motor * 0.35

func _detectar_aterrizaje(delta: float) -> void:
	var en_suelo := rueda_trasera.is_in_contact() or rueda_delantera.is_in_contact()
	if not en_suelo:
		_tiempo_aire += delta
		_pico_vy = maxf(_pico_vy, absf(linear_velocity.y))
	elif not _en_suelo_prev and _tiempo_aire > 0.08:
		aterrizaje.emit(_pico_vy)
		_pico_vy = 0.0
		_tiempo_aire = 0.0
	_en_suelo_prev = en_suelo

func _esculpir_surco(delta: float) -> void:
	if not rueda_trasera.is_in_contact(): return
	var lateral := transform.basis.x
	var lat_v := absf(linear_velocity.dot(lateral))
	var rapidez := linear_velocity.length()
	if lat_v < desliz_minimo or rapidez < 6.0: return
	_timer_surco -= delta
	if _timer_surco > 0.0: return
	_timer_surco = intervalo_surco
	var p := rueda_trasera.global_position + Vector3.DOWN * 0.1
	var dir := -transform.basis.z
	surco_creado.emit(p, dir, lat_v)

func _estabilizar() -> void:
	var en_suelo := rueda_trasera.is_in_contact() or rueda_delantera.is_in_contact()
	if en_suelo:
		var up_local := global_transform.basis.y
		apply_torque(up_local.cross(Vector3.UP) * par_estabilizacion)

func reset_estabilidad() -> void:
	_pico_vy = 0.0
	_giro_actual = 0.0
	_timer_surco = 0.0
	_tiempo_aire = 0.0
"""

ARCHIVOS["scripts/CamaraMoto.gd"] = r"""class_name CamaraMoto
extends Camera3D

@export var objetivo: VehicleBody3D
@export var distancia: float = 6.0
@export var altura: float = 2.6
@export var suavizado: float = 6.0
@export var look_ahead: float = 4.0
@export var fov_base: float = 72.0
@export var fov_max: float = 90.0
@export var fov_velocidad_max: float = 40.0
@export var trauma_decay: float = 1.4
@export var shake_max: float = 0.5
@export var shake_rot_max: float = 0.08
@export var escala_sacudida: float = 1.0

var trauma: float = 0.0
var _rng := RandomNumberGenerator.new()

func _ready() -> void:
	fov = fov_base
	current = true
	_rng.randomize()

func add_trauma(v: float) -> void:
	trauma = clampf(trauma + v, 0.0, 1.0)

func _process(delta: float) -> void:
	if objetivo == null: return
	var v := objetivo.linear_velocity.length()
	var fov_obj := lerpf(fov_base, fov_max, clampf(v / fov_velocidad_max, 0.0, 1.0))
	fov = lerpf(fov, fov_obj, delta * 3.0)

	var pos_obj := objetivo.global_position
	var b := objetivo.global_transform.basis
	var detras := pos_obj + b.z * distancia + Vector3.UP * altura
	var adelante := pos_obj - b.z * look_ahead
	var t := clampf(delta * suavizado, 0.0, 1.0)
	global_position = global_position.lerp(detras, t)
	look_at(adelante, Vector3.UP)

	if trauma > 0.001 and escala_sacudida > 0.0:
		var s := trauma * trauma
		global_position += Vector3(_rng.randf_range(-1,1), _rng.randf_range(-1,1), _rng.randf_range(-1,1)) * s * shake_max * escala_sacudida
		rotate_object_local(Vector3.UP, _rng.randf_range(-1,1) * s * shake_rot_max * escala_sacudida)
		trauma = maxf(0.0, trauma - trauma_decay * delta)
"""

ARCHIVOS["scripts/HUD.gd"] = r"""class_name HUD
extends CanvasLayer

var barra_est: ProgressBar
var etiqueta: Label
var flash: ColorRect

func _ready() -> void:
	barra_est = ProgressBar.new()
	barra_est.max_value = 1.0
	barra_est.value = 1.0
	barra_est.size = Vector2(260, 22)
	barra_est.position = Vector2(30, 30)
	add_child(barra_est)

	etiqueta = Label.new()
	etiqueta.position = Vector2(30, 60)
	etiqueta.add_theme_font_size_override("font_size", 20)
	add_child(etiqueta)

	flash = ColorRect.new()
	flash.color = Color(0, 0, 0, 0)
	flash.size = Vector2(1920, 1080)
	flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(flash)

func actualizar(separacion: float, estabilidad: float) -> void:
	barra_est.value = estabilidad
	etiqueta.text = "Ceniza: %.0f m" % separacion

func flash_rojo() -> void:
	flash.color = Color(0.7, 0.1, 0.1, 0.35)
	var tw := create_tween()
	tw.tween_property(flash, "color", Color(0.7, 0.1, 0.1, 0.0), 0.5)

func mostrar_fin() -> void:
	etiqueta.text = "FIN - pulsa R"
	etiqueta.position = Vector2(760, 500)
	etiqueta.add_theme_font_size_override("font_size", 40)

func reset() -> void:
	barra_est.value = 1.0
	etiqueta.text = ""
	etiqueta.position = Vector2(30, 60)
	etiqueta.add_theme_font_size_override("font_size", 20)
	flash.color = Color(0, 0, 0, 0)
"""

ARCHIVOS["scripts/Main.gd"] = r"""extends Node3D

const RutaHelice = preload("res://scripts/RutaHelice.gd")
const MotoCeniza = preload("res://scripts/MotoCeniza.gd")
const CamaraMoto = preload("res://scripts/CamaraMoto.gd")
const HUD = preload("res://scripts/HUD.gd")

const MAX_SURCOS := 100

var ruta: RutaHelice
var moto: MotoCeniza
var camara: CamaraMoto
var hud: HUD
var muro: MeshInstance3D

var progreso: float = 0.0
var separacion: float = 55.0
var estabilidad: float = 1.0
var estado: String = "jugando"
var surcos: Array = []

func _ready() -> void:
	_setup_input()
	_setup_environment()
	_setup_ruta()
	_setup_moto()
	_setup_camara()
	_setup_muro()
	_setup_hud()

func _setup_input() -> void:
	_accion("acelerar", [KEY_W])
	_accion("frenar", [KEY_S])
	_accion("girar_izq", [KEY_A])
	_accion("girar_der", [KEY_D])
	_accion("reiniciar", [KEY_R])
	_accion("pausa", [KEY_ESCAPE])

func _accion(nombre: String, teclas: Array) -> void:
	if InputMap.has_action(nombre):
		InputMap.erase_action(nombre)
	InputMap.add_action(nombre)
	for k in teclas:
		var ev := InputEventKey.new()
		ev.physical_keycode = k
		InputMap.action_add_event(nombre, ev)

func _setup_environment() -> void:
	var we := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.30, 0.18, 0.15)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.85, 0.70, 0.60)
	env.ambient_light_energy = 0.55
	env.fog_enabled = true
	env.fog_light_color = Color(0.55, 0.32, 0.25)
	env.fog_density = 0.010
	we.environment = env
	add_child(we)
	var sol := DirectionalLight3D.new()
	sol.rotation_degrees = Vector3(-52, 35, 0)
	sol.light_color = Color(1.0, 0.86, 0.72)
	sol.light_energy = 1.3
	add_child(sol)

func _setup_ruta() -> void:
	ruta = RutaHelice.new()
	add_child(ruta)

func _setup_moto() -> void:
	moto = MotoCeniza.new()
	add_child(moto)
	moto.global_position = ruta.punto_en_t(2.0) + Vector3.UP * 1.6
	moto.aterrizaje.connect(_on_aterrizaje)
	moto.choque.connect(_on_choque)
	moto.surco_creado.connect(_on_surco)

func _setup_camara() -> void:
	camara = CamaraMoto.new()
	add_child(camara)
	camara.objetivo = moto
	camara.global_position = moto.global_position + Vector3.UP * 3.0 + Vector3.BACK * 6.0

func _setup_muro() -> void:
	muro = MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(70, 22)
	muro.mesh = quad
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.10, 0.06, 0.05, 0.94)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.emission_enabled = true
	mat.emission = Color(0.55, 0.14, 0.04)
	mat.emission_energy_multiplier = 0.9
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	muro.material_override = mat
	add_child(muro)

func _setup_hud() -> void:
	hud = HUD.new()
	add_child(hud)

func _process(delta: float) -> void:
	_actualizar_surcos(delta)
	if estado != "jugando":
		return
	if moto.global_position.y < -200.0:
		_on_choque(); return
	var t_moto := ruta.t_cercano(moto.global_position)
	progreso = maxf(progreso, t_moto)
	separacion = maxf(14.0, separacion - 0.5 * delta)
	var t_muro := maxf(0.0, progreso - separacion)
	var p_muro := ruta.punto_en_t(t_muro)
	muro.global_position = p_muro + Vector3.UP * 6.0
	var hacia := moto.global_position - p_muro
	hacia.y = 0.0
	if hacia.length_squared() > 0.01:
		muro.look_at(p_muro + hacia, Vector3.UP)
	if t_muro >= t_moto - 1.0:
		_fin_partida()
	hud.actualizar(separacion, estabilidad)

func _actualizar_surcos(delta: float) -> void:
	for i in range(surcos.size() - 1, -1, -1):
		surcos[i][1] -= delta
		if surcos[i][1] <= 0.0:
			surcos[i][0].queue_free()
			surcos.remove_at(i)

func _input(event: InputEvent) -> void:
	if event.is_action_pressed("reiniciar") and estado != "jugando":
		_respawn()

func _on_aterrizaje(impacto: float) -> void:
	camara.add_trauma(clampf(impacto / 20.0, 0.0, 0.7))
	if impacto > 13.0:
		estabilidad = maxf(0.0, estabilidad - (impacto - 13.0) * 0.04)
		if estabilidad <= 0.0:
			_on_choque()

func _on_surco(pos: Vector3, dir: Vector3, _fuerza: float) -> void:
	var area := Area3D.new()
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(1.0, 0.2, 3.0)
	cs.shape = shape
	area.add_child(cs)
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(1.0, 0.06, 3.0)
	mi.mesh = bm
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.08, 0.06, 0.05)
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mi.material_override = mat
	area.add_child(mi)
	var t := ruta.t_cercano(pos)
	var p := ruta.punto_en_t(t)
	area.global_position = p + Vector3.UP * 0.15
	if (p + dir).distance_squared_to(p) > 0.01:
		area.look_at(p + dir, Vector3.UP)
	add_child(area)
	surcos.append([area, 18.0])
	if surcos.size() > MAX_SURCOS:
		var old = surcos.pop_front()
		old[0].queue_free()

func _on_choque() -> void:
	if estado != "jugando": return
	estado = "choque"
	camara.add_trauma(1.0)
	hud.flash_rojo()
	await get_tree().create_timer(1.1).timeout
	_respawn()

func _respawn() -> void:
	var t := ruta.t_cercano(moto.global_position)
	var p := ruta.punto_en_t(t)
	moto.global_transform = Transform3D(Basis(), p + Vector3.UP * 2.0)
	moto.linear_velocity = Vector3.ZERO
	moto.angular_velocity = Vector3.ZERO
	moto.reset_estabilidad()
	estabilidad = 1.0
	separacion = 55.0
	estado = "jugando"
	hud.reset()

func _fin_partida() -> void:
	if estado != "jugando": return
	estado = "choque"
	hud.mostrar_fin()
"""

ARCHIVOS["README.md"] = """# Ceniza

Vertical slice de motocross 3D con identidad propia: desciendes una
ladera en hélice mientras un muro de ceniza te persigue. Al derrapar
cavas surcos que en la siguiente vuelta se convierten en tu propia
vía o tu propio obstáculo.

## Requisitos

- Godot 4.3+ (Standard, no .NET).

## Arrancar

```bash
python setup.py       # solo la primera vez, si no clonaste con los archivos
# o simplemente:
godot --path . --editor
